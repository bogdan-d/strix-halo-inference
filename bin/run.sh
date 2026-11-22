#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../config/pins.env
source "$ROOT/config/pins.env"

usage() {
  echo 'Usage: bin/run.sh halogen|gufo|strixite pull|diagnose|start|stop|logs|status|smoke|weights' >&2
  echo '       bin/run.sh halogen|gufo|strixite logs --follow' >&2
  echo '       bin/run.sh halogen|gufo|strixite start [--weights PROFILE] [--wait] (START_TIMEOUT=300 seconds)' >&2
  exit 2
}
ENGINE="${1:-}"
ACTION="${2:-}"
case "$ENGINE" in
  pull|diagnose|start|stop|logs|status|smoke|weights) echo "Engine comes first. Use: bin/run.sh halogen|gufo|strixite $ENGINE" >&2; usage ;;
esac
FOLLOW=()
WAIT=false
PROFILE="${WEIGHTS:-default}"
shift "$(( $# >= 2 ? 2 : $# ))"
while (( $# )); do
  case "$1" in
    --follow) [[ "$ACTION" == logs && ${#FOLLOW[@]} == 0 ]] || usage; FOLLOW=(--follow) ;;
    --wait) [[ "$ACTION" == start && "$WAIT" == false ]] || usage; WAIT=true ;;
    --weights) [[ "$ACTION" == start && $# -ge 2 ]] || usage; PROFILE="$2"; shift ;;
    *) usage ;;
  esac
  shift
done
case "$ACTION" in pull|diagnose|start|stop|logs|status|smoke|weights) ;; *) usage ;; esac
case "$ENGINE" in
  halogen) IMAGE="$HALOGEN_IMAGE"; PORT=8731; HEALTH=/health ;;
  gufo) IMAGE="$GUFO_IMAGE"; PORT=8080; HEALTH=/ready ;;
  strixite) IMAGE="$STRIXITE_IMAGE"; PORT=5300; HEALTH=/health ;;
  *) echo 'Choose halogen, gufo or strixite.' >&2; usage ;;
esac
NAME="strix-halo-$ENGINE"
MODELS_DIR="${MODELS_DIR:-/home/bogdan/models}"
NPU_MODELS="${NPU_MODELS:-}"
# Holding the fabric clock costs about 2.3 W at idle, so it is held only while Halogen runs NPU models.
FABRIC_CLOCK="${FABRIC_CLOCK:-/usr/local/sbin/halogen-fabric-clock}"
CACHE_ROOT="${CACHE_ROOT:-$HOME/.cache/strix-halo-inference}"
BASE="http://127.0.0.1:$PORT"
if [[ "$WAIT" == true ]]; then
  START_TIMEOUT="${START_TIMEOUT:-300}"
  [[ "$START_TIMEOUT" =~ ^[1-9][0-9]{0,3}$ && "$START_TIMEOUT" -le 3600 ]] || { echo 'START_TIMEOUT must be 1..3600 seconds.' >&2; exit 2; }
fi
case "$ACTION" in
  weights) exec python "$ROOT/bin/weights.py" "$ENGINE" list ;;
  pull) exec podman pull "$IMAGE" ;;
  stop)
    STOP_TIMEOUT=60
    [[ "$ENGINE" != strixite ]] || STOP_TIMEOUT=90
    STATUS=0
    podman stop --time "$STOP_TIMEOUT" "$NAME" || STATUS=$?
    # Release even when the container already exited, so a failed NPU start does not keep the clock held.
    if [[ "$ENGINE" == halogen && -x "$FABRIC_CLOCK" ]] && "$FABRIC_CLOCK" status >/dev/null; then
      sudo -n "$FABRIC_CLOCK" release || STATUS=1
    fi
    free -h; exit "$STATUS" ;;
  logs)
    podman container exists "$NAME" || { echo "No container logs available for $NAME. It may be stopped and auto-removed." >&2; exit 1; }
    exec podman logs --tail 100 "${FOLLOW[@]}" "$NAME" ;;
  status) exec python "$ROOT/bin/status.py" "$ENGINE" "$NAME" "$BASE$HEALTH" ;;
  smoke)
    curl --fail --silent --show-error --max-time 10 "$BASE$HEALTH" >/dev/null
    MODEL="$(curl --fail --silent --show-error --max-time 10 "$BASE/v1/models" | python -c 'import json,sys; print(json.load(sys.stdin)["data"][0]["id"])')"
    PAYLOAD="$(python -c 'import json,sys; d={"model":sys.argv[1],"messages":[{"role":"user","content":"Reply with exactly: ready"}],"temperature":0,"max_tokens":32,"stream":False}; d.update({"reasoning_effort":"none"} if sys.argv[2]=="strixite" else {"chat_template_kwargs":{"enable_thinking":False}}); print(json.dumps(d))' "$MODEL" "$ENGINE")"
    RESPONSE="$(curl --fail --silent --show-error --max-time 180 "$BASE/v1/chat/completions" -H 'Content-Type: application/json' --data "$PAYLOAD")"
    printf '%s' "$RESPONSE" | python -c 'import json,sys; d=json.load(sys.stdin); assert d["choices"][0]["message"].get("content"), d; print(json.dumps(d,indent=2))'
    exit ;;
esac

[[ "$(podman info --format '{{.Host.Security.Rootless}}')" == true ]] || { echo 'Use rootless Podman, not sudo.' >&2; exit 1; }
# The NPU is passed to every engine so NPU features need no launcher change. Halogen uses it only when
# NPU_MODELS is set, which also needs a held fabric clock (README, NPU models). The image carries XRT.
GPU=(--device /dev/kfd --device /dev/dri --device /dev/accel/accel0 --ulimit memlock=-1:-1)
if [[ "$(podman info --format '{{.Host.OCIRuntime.Name}}')" == crun ]]; then
  GPU+=(--group-add keep-groups)
else
  echo 'Runtime is not crun. GPU access must work without preserved supplementary groups.' >&2
fi
if [[ "$ACTION" == diagnose ]]; then
  if [[ "$ENGINE" == gufo ]]; then
    exec podman run --rm --network none "${GPU[@]}" "$IMAGE" gufo diagnose
  fi
  if [[ "$ENGINE" == strixite ]]; then
    # The release has no GPU diagnostic command. Help exits before model allocation.
    exec podman run --rm --network none "${GPU[@]}" "$IMAGE" --help
  fi
  exec podman run --rm --network none "${GPU[@]}" --entrypoint /bin/sh "$IMAGE" -c 'ulimit -l; rocminfo'
fi

SELECTION="$(python "$ROOT/bin/weights.py" "$ENGINE" launch "$PROFILE")"
mapfile -t WEIGHT_PATHS <<<"$SELECTION"
# A LoRA adapter is merged into the stock weights at load: by the IQ extension when the profile uses it, otherwise
# by the local fork build, since the pinned image's built-in provider cannot.
ADAPTER="${WEIGHT_PATHS[3]:-}"
DFLASH_MODEL="${WEIGHT_PATHS[4]}"
SERVED_MODEL="${WEIGHT_PATHS[5]}"
MAX_CONTEXT="${WEIGHT_PATHS[6]}"
if [[ -n "$ADAPTER" && -z "${WEIGHT_PATHS[2]:-}" ]]; then
  IMAGE="$GUFO_FORK_IMAGE"
  podman image exists "$IMAGE" || { echo "Local Gufo fork image missing: $IMAGE. Build it with bin/gufo-fork.sh (docs/weight-profiles.md)." >&2; exit 1; }
fi
if [[ "$ENGINE" == gufo && -n "${GUFO_MODEL:-}" && "$PROFILE" != default ]]; then
  echo 'Choose either --weights/WEIGHTS or GUFO_MODEL, not both.' >&2; exit 2
fi
if [[ "$PROFILE" == default ]]; then
  "$ROOT/bin/models.sh" check "$ENGINE"
else
  "$ROOT/bin/models.sh" check "$ENGINE" "$PROFILE"
fi
NPU=()
if [[ -n "$NPU_MODELS" ]]; then
  [[ "$ENGINE" == halogen && "$ACTION" == start ]] || { echo 'NPU_MODELS applies only to bin/run.sh halogen start.' >&2; exit 2; }
  [[ "$NPU_MODELS" =~ ^[a-z0-9][a-z0-9.-]*(,[a-z0-9][a-z0-9.-]*)*$ ]] || { echo 'NPU_MODELS must be comma-separated model ids.' >&2; exit 2; }
  IFS=, read -r -a IDS <<<"$NPU_MODELS"
  for ID in "${IDS[@]}"; do
    # Only models whose own weights are in the manifest can load; devices-only entries cannot.
    awk -F'\t' -v path="$ID/$ID.hnpw" '$3 == path {found = 1} END {exit !found}' "$ROOT/config/npu-files.tsv" \
      || { echo "NPU model $ID is not in config/npu-files.tsv. Add it with bin/npu-manifest.sh, then bin/models.sh download npu." >&2; exit 2; }
  done
  "$ROOT/bin/models.sh" check npu
  # Rootless containers cannot lock more than the user may. NPU models need GiBs; systemd's default is 8 MiB.
  MEMLOCK="${MEMLOCK_KIB:-$(ulimit -H -l)}"
  [[ "$MEMLOCK" == unlimited || "$MEMLOCK" -ge 4194304 ]] || { echo "Locked-memory limit is $MEMLOCK KiB; NPU models need several GiB. Raise LimitMEMLOCK (README, NPU models)." >&2; exit 1; }
  NPU+=(--env "HALOGEN_NPU_MODELS=$NPU_MODELS")
fi
mkdir -p -- "$CACHE_ROOT/$ENGINE"
exec 9>"$CACHE_ROOT/start.lock"
flock -n 9 || { echo 'Another engine start is in progress.' >&2; exit 1; }
ACTIVE="$(podman ps --filter label=io.strix-halo-inference.managed=true --format '{{.Names}}')"
[[ -z "$ACTIVE" ]] || { echo "Stop the active engine first: $ACTIVE" >&2; exit 1; }
COMFY="$(podman ps --filter name=^strix-halo-den-comfyui$ --format '{{.Names}}')"
[[ -z "$COMFY" ]] || { echo "Stop ComfyUI in Den before starting inference: $COMFY" >&2; exit 1; }
CONTEXT="${CONTEXT:-$MAX_CONTEXT}"
MIN_CONTEXT=1024
[[ "$ENGINE" != strixite ]] || MIN_CONTEXT=4096
[[ "$CONTEXT" =~ ^[0-9]+$ && "$CONTEXT" -ge "$MIN_CONTEXT" && "$CONTEXT" -le "$MAX_CONTEXT" ]] || { echo "CONTEXT must be $MIN_CONTEXT..$MAX_CONTEXT." >&2; exit 2; }
SPECULATIVE="${SPECULATIVE:-on}"
case "$SPECULATIVE" in on|off) ;; *) echo 'SPECULATIVE must be on or off.' >&2; exit 2 ;; esac
# 8-bit attention cache on Halogen and Strixite: about 0.6 of the 16-bit cache's memory. Gufo has no such setting.
KV8="${KV8:-on}"
case "$KV8" in on|off) ;; *) echo 'KV8 must be on or off.' >&2; exit 2 ;; esac
# Image input: on by default for Strixite, opt-in for Halogen. bin/models.sh fetches both engines' vision files.
DEFAULT_VISION=off
[[ "$ENGINE" != strixite ]] || DEFAULT_VISION=on
VISION="${VISION:-$DEFAULT_VISION}"
case "$VISION" in on|off) ;; *) echo 'VISION must be on or off.' >&2; exit 2 ;; esac
[[ "$ENGINE" != gufo || "$VISION" == off ]] || { echo 'VISION=on applies only to Halogen and Strixite.' >&2; exit 2; }
# Strixite conversations served at once. Each slot can grow to a full-capacity K/V state.
SLOTS="${SLOTS:-1}"
[[ "$SLOTS" =~ ^[1-8]$ ]] || { echo 'SLOTS must be 1..8.' >&2; exit 2; }
# Gufo trial model: the first shard of another GGUF under the models directory, served instead of the pinned
# file. Trial files are outside bin/models.sh's manifests; the MTP head stays the pinned one.
if [[ "$ENGINE" == gufo && -n "${GUFO_MODEL:-}" ]]; then
  [[ "$GUFO_MODEL" != /* && "$GUFO_MODEL" != *..* && "$GUFO_MODEL" == *.gguf && -f "$MODELS_DIR/$GUFO_MODEL" ]] \
    || { echo "GUFO_MODEL must be a .gguf file under $MODELS_DIR, given relative to it." >&2; exit 2; }
fi
WEIGHT_LABEL="$PROFILE"
[[ "$ENGINE" != gufo || -z "${GUFO_MODEL:-}" ]] || WEIGHT_LABEL=custom
GUFO_MODEL="${GUFO_MODEL:-${WEIGHT_PATHS[0]}}"
ENGINE_CACHE="$CACHE_ROOT/$ENGINE/$WEIGHT_LABEL"
mkdir -p -- "$ENGINE_CACHE"
ARGS=(podman run --detach --rm --name "$NAME" --label io.strix-halo-inference.managed=true
  --label "io.strix-halo-inference.weights=$WEIGHT_LABEL"
  "${GPU[@]}" --publish "127.0.0.1:$PORT:$PORT"
  --volume "$MODELS_DIR:/models:ro" --volume "$ENGINE_CACHE:/cache:rw")
if [[ "$ENGINE" == halogen ]]; then
  ARGS+=(--ipc=host "${NPU[@]}"
    --env "HALOGEN_CHECKPOINT=/models/${WEIGHT_PATHS[0]}"
    --env "HALOGEN_TOKENIZER=/models/${WEIGHT_PATHS[0]%/*}/tokenizer"
    --env "HALOGEN_CTX=$CONTEXT" --env "HALOGEN_KV_POOL_POSITIONS=$CONTEXT"
    --env HALOGEN_KV_SLOTS=1 --env HALOGEN_CACHE_DIR=/cache --env HALOGEN_CACHE_DISK_GIB=16)
  [[ "$SPECULATIVE" == on ]] || ARGS+=(--env HALOGEN_DRAFTER_DEFAULT=0 --env HALOGEN_PLD=0)
  [[ "$KV8" == off ]] || ARGS+=(--env HALOGEN_KV8=1)
  [[ "$VISION" == off ]] || ARGS+=(--env "HALOGEN_VISION_TOWER=/models/${WEIGHT_PATHS[0]%/*}/qwen38-flash-next-vision.hgn")
  ARGS+=("$IMAGE")
elif [[ "$ENGINE" == gufo ]]; then
  if [[ -n "${WEIGHT_PATHS[2]:-}" ]]; then
    ARGS+=(--volume "${WEIGHT_PATHS[2]}:/extensions:ro" --env GUFO_EXTENSIONS_DIR=/extensions)
  fi
  ARGS+=("--userns=keep-id:uid=1000,gid=1000" "$IMAGE" gufo serve --host 0.0.0.0 --port "$PORT" --sessions 1 llm
    --model "/models/$GUFO_MODEL"
    --served-model-name "$SERVED_MODEL" --context "$CONTEXT"
    --cache-ram-bytes 2147483648 --cache-disk /cache
    --cache-disk-bytes 17179869184)
  if [[ "$SPECULATIVE" == off ]]; then
    ARGS+=(--speculative off)
  elif [[ -n "$DFLASH_MODEL" ]]; then
    ARGS+=(--speculative dflash2 --dflash-model "/models/$DFLASH_MODEL")
  else
    [[ -n "${WEIGHT_PATHS[1]}" ]] || { echo "Gufo profile $PROFILE needs a draft model or SPECULATIVE=off." >&2; exit 2; }
    ARGS+=(--speculative mtp --mtp-model "/models/${WEIGHT_PATHS[1]}")
  fi
  [[ -z "$ADAPTER" ]] || ARGS+=(--lora "/models/$ADAPTER")
else
  ARGS+=(--stop-timeout 90 --env "STRIX_MODELS_DIR=/models/${WEIGHT_PATHS[0]}" "$IMAGE"
    --host 0.0.0.0 --port "$PORT" --model-id "$SERVED_MODEL"
    --capacity "$CONTEXT" --rope-yarn-factor 1 --mtp "$SPECULATIVE"
    --prompt-cache-dir /cache --prompt-cache-gib 16 --prompt-cache-ram-margin-gib 8
    --low-memory fail --think-nudge off --vision "$VISION" --total-slots "$SLOTS")
  if [[ "$KV8" == on ]]; then ARGS+=(--kv-cache q8); else ARGS+=(--kv-cache bf16); fi
fi
if [[ -n "$NPU_MODELS" ]]; then
  sudo -n "$FABRIC_CLOCK" hold || { echo "Could not hold the GPU fabric clock. Install $FABRIC_CLOCK and its sudoers rule (README, NPU models)." >&2; exit 1; }
fi
printf 'Starting %s:' "$ENGINE"; printf ' %q' "${ARGS[@]}"; echo
# Keep the startup lock in this shell, not the detached container monitor.
CID="$("${ARGS[@]}" 9>&-)" || { [[ -z "$NPU_MODELS" ]] || sudo -n "$FABRIC_CLOCK" release; exit 1; }
echo "$CID"
exec 9>&-
echo "Container started, not yet ready. Check bin/run.sh $ENGINE status and bin/run.sh $ENGINE logs"
if [[ "$WAIT" == true ]]; then
  trap 'echo "Stopped waiting. Container was not stopped. Inspect its status or logs." >&2; exit 130' INT
  trap 'echo "Stopped waiting. Container was not stopped. Inspect its status or logs." >&2; exit 143' TERM
  DEADLINE=$((SECONDS + START_TIMEOUT))
  while (( SECONDS < DEADLINE )); do
    RUNNING="$(timeout 5 podman inspect --format '{{.State.Running}}' "$CID")" || { echo "Cannot inspect startup container $CID. Check bin/run.sh $ENGINE logs." >&2; exit 1; }
    [[ "$RUNNING" == true ]] || { echo "Container exited before readiness. Check bin/run.sh $ENGINE logs." >&2; exit 1; }
    REMAINING=$((DEADLINE - SECONDS))
    (( REMAINING > 0 )) || break
    PROBE=$((REMAINING < 5 ? REMAINING : 5))
    if curl --fail --silent --max-time "$PROBE" "$BASE$HEALTH" >/dev/null; then
      echo "$ENGINE ready at $BASE/v1"
      echo "With the installed Pi profile: pi --provider $ENGINE --model $SERVED_MODEL --thinking xhigh"
      [[ "$ENGINE" != strixite ]] || echo 'Normal Pi tools are not sandboxed. See docs/strixite.md for the guarded coding-test boundary.'
      exit
    fi
    sleep 1
  done
  echo "Startup timeout after ${START_TIMEOUT}s: engine is not ready. Container was not stopped. Inspect bin/run.sh $ENGINE logs or use bin/run.sh $ENGINE stop." >&2
  exit 1
fi
