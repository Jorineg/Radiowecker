#!/usr/bin/env bash
set -euo pipefail

WIFI_FILE_NAME="wifi.txt"

log() {
  echo "import-wifi: $*" | systemd-cat -t import-wifi -p info
}

err() {
  echo "import-wifi: $*" | systemd-cat -t import-wifi -p err
}

require_nmcli() {
  if ! command -v nmcli >/dev/null 2>&1; then
    err "nmcli not found; NetworkManager must be installed."
    exit 0
  fi
}

# Find candidate wifi.txt paths
find_wifi_files() {
  local -a paths=()
  # Common boot mount points
  for p in "/boot/${WIFI_FILE_NAME}" "/boot/firmware/${WIFI_FILE_NAME}"; do
    [[ -f "$p" ]] && paths+=("$p")
  done

  # Any mounted vfat partition
  while IFS= read -r mp; do
    [[ -n "$mp" && -f "${mp}/${WIFI_FILE_NAME}" ]] && paths+=("${mp}/${WIFI_FILE_NAME}")
  done < <(lsblk -rno MOUNTPOINT,FSTYPE | awk '$2=="vfat" && $1!="" {print $1}')

  printf '%s\n' "${paths[@]}" | awk 'NF' | sort -u
}

sanitize_con_name() {
  # Create a safe connection name from SSID
  local ssid="$1"
  local con="provisioned-${ssid//[^A-Za-z0-9_.-]/_}"
  printf '%s' "$con"
}

ensure_connection() {
  # Creates or updates a NM connection for the given SSID.
  # Args: ssid psk hidden priority
  local ssid="$1"
  local psk="${2-}"
  local hidden="${3-0}"
  local priority="${4-}"

  local con_name
  con_name="$(sanitize_con_name "$ssid")"

  if nmcli -t -f NAME,TYPE connection show 2>/dev/null | awk -F: -v n="$con_name" '$2=="wifi" && $1==n {found=1} END{exit !found}'; then
    log "Updating existing connection: $con_name (SSID: $ssid)"
  else
    log "Creating new connection: $con_name (SSID: $ssid)"
    nmcli connection add type wifi con-name "$con_name" ssid "$ssid" >/dev/null
  fi

  if [[ -n "$psk" ]]; then
    nmcli connection modify "$con_name" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$psk"
  else
    nmcli connection modify "$con_name" wifi-sec.key-mgmt none
  fi

  if [[ "${hidden}" == "1" || "${hidden,,}" == "yes" || "${hidden,,}" == "true" ]]; then
    nmcli connection modify "$con_name" 802-11-wireless.hidden yes
  else
    nmcli connection modify "$con_name" 802-11-wireless.hidden no
  fi

  if [[ -n "${priority}" ]]; then
    nmcli connection modify "$con_name" connection.autoconnect-priority "$priority"
  fi

  nmcli connection modify "$con_name" connection.autoconnect yes
  nmcli connection reload >/dev/null || true

  # Do not force an immediate connect; autoconnect will handle it.
  log "Provisioned Wi-Fi: SSID='$ssid' (password hidden), autoconnect=on"
}

process_wifi_file() {
  local file="$1"
  log "Processing $file"

  local line key val
  local ssid="" psk="" hidden="0" priority=""
  local ok_all=1

  flush_entry() {
    # Process current block if it has an SSID
    if [[ -n "$ssid" ]]; then
      if ! ensure_connection "$ssid" "$psk" "$hidden" "$priority"; then
        err "Failed to add SSID '$ssid' from $file"
        ok_all=0
      fi
      # reset for next block
      ssid="" psk="" hidden="0" priority=""
    fi
  }

  # Read Windows CRLF-friendly, allow blank lines to separate entries
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"            # strip CR if present
    [[ -z "${line// }" ]] && { flush_entry; continue; }  # blank line => new block
    # key=value
    if [[ "$line" =~ ^[[:space:]]*([^=#[:space:]]+)[[:space:]]*=[[:space:]]*(.*)$ ]]; then
      key="${BASH_REMATCH[1],,}"
      val="${BASH_REMATCH[2]}"
      # Trim surrounding quotes and whitespace
      val="${val#\"}"; val="${val%\"}"
      val="${val#"${val%%[![:space:]]*}"}"
      val="${val%"${val##*[![:space:]]}"}"
      case "$key" in
        ssid) ssid="$val" ;;
        psk|password|pass|wpa|wpa_psk) psk="$val" ;;
        hidden) hidden="$val" ;;
        priority) priority="$val" ;;
        *) ;; # ignore unknown keys
      esac
    fi
  done < "$file"

  # flush the last entry
  flush_entry

  if [[ "$ok_all" -eq 1 ]]; then
    log "Successfully imported all entries in $file; deleting file."
    rm -f -- "$file" || err "Could not delete $file; remove it manually."
  else
    err "One or more entries failed in $file; leaving file in place for retry."
  fi
}

main() {
  require_nmcli
  local files
  mapfile -t files < <(find_wifi_files)

  if [[ "${#files[@]}" -eq 0 ]]; then
    log "No $WIFI_FILE_NAME found on boot/firmware or mounted FAT32 partitions."
    exit 0
  fi

  for f in "${files[@]}"; do
    process_wifi_file "$f"
  done
}

main "$@"