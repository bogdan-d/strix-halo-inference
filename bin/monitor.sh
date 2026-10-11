#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="$ROOT/config/monitoring"
# shellcheck source=../config/monitoring/pins.env
source "$CONFIG/pins.env"
LABEL=io.strix-halo-inference.monitoring
COMPONENTS=(exporter probe prometheus)
DASHBOARD="file://$CONFIG/dashboard.html"
select_component() {
  NAME="strix-halo-monitor-$1"
  case "$1" in
    exporter) IMAGE="$EXPORTER_IMAGE"; URL=http://127.0.0.1:9100/metrics ;;
    probe) IMAGE="$PROBE_IMAGE"; URL=http://127.0.0.1:9115/metrics ;;
    prometheus) IMAGE="$PROMETHEUS_IMAGE"; URL=http://127.0.0.1:9090/-/ready ;;
  esac
}
usage() {
  echo 'Usage: bin/monitor.sh pull|start|stop|status' >&2
  echo '       bin/monitor.sh exporter|probe|prometheus logs [--follow]' >&2
  exit 2
}
ACTION="${1:-}"
case "$ACTION" in
  exporter|probe|prometheus)
    [[ $# == 2 || ( $# == 3 && "$3" == --follow ) ]] || usage
    [[ "$2" == logs ]] || usage
    NAME="strix-halo-monitor-$ACTION"
    podman container exists "$NAME" || { echo "No retained container logs for $NAME." >&2; exit 1; }
    [[ "$(podman container inspect --format "{{index .Config.Labels \"$LABEL\"}}" "$NAME")" == true ]] || {
      echo "Refusing unrelated container: $NAME" >&2; exit 1;
    }
    FOLLOW=()
    [[ $# == 2 ]] || FOLLOW=(--follow)
    exec podman logs --tail 100 "${FOLLOW[@]}" "$NAME"
    ;;
  pull|start|stop|status) [[ $# == 1 ]] || usage ;;
  *) usage ;;
esac

# Refuse to act on unrelated containers or volumes occupying our names.
owned() {
  local kind="$1" name="$2" field=Labels
  [[ "$kind" != container ]] || field=Config.Labels
  [[ "$(podman "$kind" inspect --format "{{index .$field \"$LABEL\"}}" "$name")" == true ]] || {
    echo "Refusing unrelated $kind: $name" >&2; return 1;
  }
}
if [[ "$ACTION" == pull ]]; then
  for component in "${COMPONENTS[@]}"; do select_component "$component"; podman pull "$IMAGE"; done
  exit
fi
if [[ "$ACTION" == status ]]; then
  FAILED=0
  for component in "${COMPONENTS[@]}"; do
    select_component "$component"
    if podman container exists "$NAME" && owned container "$NAME" &&
      [[ "$(podman container inspect --format '{{.State.Running}}' "$NAME")" == true ]] &&
      curl --noproxy '*' -fsS --max-time 3 "$URL" >/dev/null; then
      echo "$component: ready ($URL)"
    else
      echo "$component: unavailable"; FAILED=1
    fi
  done
  echo "Dashboard: $DASHBOARD"
  exit "$FAILED"
fi
exec 9>"$CONFIG/.lock"
flock -n 9 || { echo 'Another monitoring start or stop is in progress.' >&2; exit 1; }
if [[ "$ACTION" == stop ]]; then
  FAILED=0
  for component in prometheus probe exporter; do
    NAME="strix-halo-monitor-$component"
    if podman container exists "$NAME"; then
      if owned container "$NAME"; then
        podman stop --time 30 "$NAME" || FAILED=1
      else FAILED=1; fi
    fi
  done
  if [[ "$FAILED" == 0 ]]; then echo 'Monitoring stopped. Persistent volumes are retained.'
  else echo 'Monitoring stop incomplete. Inspect the errors above.' >&2; fi
  exit "$FAILED"
fi

for component in "${COMPONENTS[@]}"; do
  select_component "$component"
  if podman container exists "$NAME"; then
    echo "Container $NAME already exists. Inspect it or stop monitoring first." >&2; exit 1
  fi
  podman image exists "$IMAGE" || { echo 'Missing monitoring image. Run bin/monitor.sh pull first.' >&2; exit 1; }
done
NAME=strix-halo-monitor-prometheus
if podman volume exists "$NAME"; then owned volume "$NAME"
else podman volume create --label "$LABEL=true" "$NAME" >/dev/null; fi

STARTED=()
READY=false
cleanup() {
  local result=$?
  trap - EXIT
  if [[ "$READY" != true ]]; then
    echo 'Monitoring startup failed. Stopping only containers started by this invocation.' >&2
    for cid in "${STARTED[@]}"; do
      podman stop --ignore --time 10 "$cid" || echo "Cleanup failed for container $cid" >&2
    done
  fi
  exit "$result"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
# Keep the lifecycle lock out of conmon and bind all services to host loopback.
COMMON=(--detach --rm --pull=never --network host --read-only --cap-drop all
  --security-opt no-new-privileges --label "$LABEL=true" --log-driver=k8s-file --log-opt max-size=10mb)
CID=$(podman run "${COMMON[@]}" --name strix-halo-monitor-exporter \
  -v /proc/stat:/host/proc/stat:ro -v /proc/meminfo:/host/proc/meminfo:ro \
  -v /proc/diskstats:/host/proc/diskstats:ro -v /proc/vmstat:/host/proc/vmstat:ro \
  -v /proc/pressure:/host/proc/pressure:ro -v /sys:/host/sys:ro \
  "$EXPORTER_IMAGE" --path.procfs=/host/proc --path.sysfs=/host/sys \
  --web.listen-address=127.0.0.1:9100 --collector.disable-defaults \
  --collector.cpu --collector.meminfo --collector.vmstat --collector.diskstats \
  --collector.pressure --collector.drm --collector.hwmon 9>&-)
STARTED+=("$CID")
CID=$(podman run "${COMMON[@]}" --name strix-halo-monitor-probe \
  -v "$CONFIG/blackbox.yml:/etc/blackbox_exporter/config.yml:ro" \
  "$PROBE_IMAGE" --config.file=/etc/blackbox_exporter/config.yml \
  --web.listen-address=127.0.0.1:9115 --log.prober=warn 9>&-)
STARTED+=("$CID")
CID=$(podman run "${COMMON[@]}" --name strix-halo-monitor-prometheus \
  --userns=keep-id:uid=65534,gid=65534 \
  -v strix-halo-monitor-prometheus:/prometheus \
  -v "$CONFIG/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  "$PROMETHEUS_IMAGE" --config.file=/etc/prometheus/prometheus.yml \
  --storage.tsdb.path=/prometheus --storage.tsdb.retention.time=7d \
  --storage.tsdb.retention.size=2GB --web.listen-address=127.0.0.1:9090 9>&-)
STARTED+=("$CID")
DEADLINE=$((SECONDS + 60))
for component in "${COMPONENTS[@]}"; do
  select_component "$component"
  while true; do
    [[ $SECONDS -lt $DEADLINE ]] || { echo 'Monitoring readiness timed out after 60 seconds.' >&2; exit 1; }
    [[ "$(podman container inspect --format '{{.State.Running}}' "$NAME")" == true ]] || {
      echo "$component exited before readiness at $URL." >&2
      podman logs --tail 30 "$NAME" >&2; exit 1;
    }
    if curl --noproxy '*' -fsS --max-time 2 "$URL" >/dev/null 2>&1; then break; fi
    sleep 1
  done
done
for cid in "${STARTED[@]}"; do
  [[ "$(podman container inspect --format '{{.State.Running}}' "$cid")" == true ]] || exit 1
done
READY=true
echo "Monitoring ready. Dashboard: $DASHBOARD"
