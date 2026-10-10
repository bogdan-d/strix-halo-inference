#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/pins.env
source "$ROOT/config/pins.env"

usage() {
  echo 'Usage: bin/run.sh halogen|gufo pull|diagnose|start|stop|logs|status|smoke' >&2
  echo '       bin/run.sh halogen|gufo logs --follow' >&2
  exit 2
}
ENGINE="${1:-}"
ACTION="${2:-}"
case "$ENGINE" in
  pull|diagnose|start|stop|logs|status|smoke) echo "Engine comes first. Use: bin/run.sh halogen|gufo $ENGINE" >&2; usage ;;
esac
FOLLOW=()
if [[ $# == 3 && "$ACTION" == logs && "$3" == --follow ]]; then
  FOLLOW=(--follow)
else
  [[ $# == 2 ]] || usage
fi
case "$ACTION" in pull|diagnose|start|stop|logs|status|smoke) ;; *) usage ;; esac
case "$ENGINE" in
  halogen) IMAGE="$HALOGEN_IMAGE"; PORT=8731; REPO="$HALOGEN_REPO"; HEALTH=/health ;;
  gufo) IMAGE="$GUFO_IMAGE"; PORT=8080; REPO="$GUFO_REPO"; HEALTH=/ready ;;
  *) echo 'Choose halogen or gufo.' >&2; usage ;;
esac
NAME="strix-halo-$ENGINE"
MODELS_DIR="${MODELS_DIR:-/home/bogdan/models}"
CACHE_ROOT="${CACHE_ROOT:-$HOME/.cache/strix-halo-inference}"
BASE="http://127.0.0.1:$PORT"
case "$ACTION" in
  pull) exec podman pull "$IMAGE" ;;
  stop) podman stop --time 60 "$NAME"; free -h; exit ;;
  logs)
    podman container exists "$NAME" || { echo "No container logs available for $NAME. It may be stopped and auto-removed." >&2; exit 1; }
    exec podman logs --tail 100 "${FOLLOW[@]}" "$NAME" ;;
  status) podman ps -a --filter "name=^$NAME$"; curl --fail --silent --show-error --max-time 5 "$BASE$HEALTH"; echo; exit ;;
  smoke)
    curl --fail --silent --show-error --max-time 10 "$BASE$HEALTH" >/dev/null
    MODEL="$(curl --fail --silent --show-error --max-time 10 "$BASE/v1/models" | python -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')"
    PAYLOAD="$(python -c 'import json,sys; print(json.dumps({"model":sys.argv[1],"messages":[{"role":"user","content":"Reply with exactly: ready"}],"temperature":0,"max_tokens":32,"chat_template_kwargs":{"enable_thinking":False},"stream":False}))' "$MODEL")"
    RESPONSE="$(curl --fail --silent --show-error --max-time 180 "$BASE/v1/chat/completions" -H 'Content-Type: application/json' --data "$PAYLOAD")"
    printf '%s' "$RESPONSE" | python -c 'import json,sys; d=json.load(sys.stdin); assert d["choices"][0]["message"].get("content"), d; print(json.dumps(d,indent=2))'
    exit ;;
esac

[[ "$(podman info --format '{{.Host.Security.Rootless}}')" == true ]] || { echo 'Use rootless Podman, not sudo.' >&2; exit 1; }
GPU=(--device /dev/kfd --device /dev/dri --ulimit memlock=-1:-1)
if [[ "$(podman info --format '{{.Host.OCIRuntime.Name}}')" == crun ]]; then
  GPU+=(--group-add keep-groups)
else
  echo 'Runtime is not crun. GPU access must work without preserved supplementary groups.' >&2
fi
if [[ "$ACTION" == diagnose ]]; then
  if [[ "$ENGINE" == gufo ]]; then
    exec podman run --rm --network none "${GPU[@]}" "$IMAGE" gufo diagnose
  fi
  exec podman run --rm --network none "${GPU[@]}" --entrypoint /bin/sh "$IMAGE" -c 'ulimit -l; rocminfo'
fi

"$ROOT/bin/models.sh" check "$ENGINE"
mkdir -p -- "$CACHE_ROOT/$ENGINE"
exec 9>"$CACHE_ROOT/start.lock"
flock -n 9 || { echo 'Another engine start is in progress.' >&2; exit 1; }
ACTIVE="$(podman ps --filter label=io.strix-halo-inference.managed=true --format '{{.Names}}')"
[[ -z "$ACTIVE" ]] || { echo "Stop the active engine first: $ACTIVE" >&2; exit 1; }
CONTEXT="${CONTEXT:-262144}"
[[ "$CONTEXT" =~ ^[0-9]+$ && "$CONTEXT" -ge 1024 && "$CONTEXT" -le 262144 ]] || { echo 'CONTEXT must be 1024..262144.' >&2; exit 2; }
SPECULATIVE="${SPECULATIVE:-on}"
case "$SPECULATIVE" in on|off) ;; *) echo 'SPECULATIVE must be on or off.' >&2; exit 2 ;; esac
ARGS=(podman run --detach --rm --name "$NAME" --label io.strix-halo-inference.managed=true
  "${GPU[@]}" --publish "127.0.0.1:$PORT:$PORT"
  --volume "$MODELS_DIR:/models:ro" --volume "$CACHE_ROOT/$ENGINE:/cache:rw")
if [[ "$ENGINE" == halogen ]]; then
  ARGS+=(--ipc=host
    --env "HALOGEN_CHECKPOINT=/models/$REPO/qwen38-flash-next-v2.hgn"
    --env "HALOGEN_TOKENIZER=/models/$REPO/tokenizer"
    --env "HALOGEN_CTX=$CONTEXT" --env "HALOGEN_KV_POOL_POSITIONS=$CONTEXT"
    --env HALOGEN_KV_SLOTS=1 --env HALOGEN_CACHE_DIR=/cache --env HALOGEN_CACHE_DISK_GIB=16)
  [[ "$SPECULATIVE" == on ]] || ARGS+=(--env HALOGEN_DRAFTER_DEFAULT=0 --env HALOGEN_PLD=0)
  ARGS+=("$IMAGE")
else
  ARGS+=("--userns=keep-id:uid=1000,gid=1000" "$IMAGE" gufo serve --host 0.0.0.0 --port "$PORT" --sessions 1 llm
    --model "/models/$REPO/UD-Q4_K_XL/Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf"
    --served-model-name qwen3.8-flash-next --context "$CONTEXT"
    --cache-ram-bytes 2147483648 --cache-disk /cache
    --cache-disk-bytes 17179869184 --cache-disk-staging-bytes 2147483648)
  if [[ "$SPECULATIVE" == on ]]; then
    ARGS+=(--speculative mtp --mtp-model "/models/$REPO/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf")
  else
    ARGS+=(--speculative off)
  fi
fi
printf 'Starting %s:' "$ENGINE"; printf ' %q' "${ARGS[@]}"; echo
# Keep the startup lock in this shell, not the detached container monitor.
"${ARGS[@]}" 9>&-
echo "Container started, not yet ready. Check bin/run.sh $ENGINE status and bin/run.sh $ENGINE logs"
