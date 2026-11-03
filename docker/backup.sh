#!/bin/sh
# Daily PostgreSQL backup (backup service in docker-compose.prod.yml).
#   - pg_dump in custom format (-Fc) to /backups/prasibali-YYYYmmdd-HHMM.dump once a day at BACKUP_AT (local TZ)
#   - deletes dumps older than BACKUP_KEEP_DAYS
#   - `backup.sh now` makes one dump immediately and exits (manual backup or test)
# Connection settings come from PGHOST/PGDATABASE/PGUSER/PGPASSWORD; the password is never printed.
set -eu

KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
AT="${BACKUP_AT:-02:00}"

log() {
    printf '{"time":"%s","level":"%s","logger":"backup","message":"%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2"
}

dump() {
    file="/backups/prasibali-$(date +%Y%m%d-%H%M).dump"
    if pg_dump -Fc --no-owner --file "$file.part"; then
        mv "$file.part" "$file"
        log INFO "Backup written: $(basename "$file") ($(du -h "$file" | cut -f1))"
    else
        rm -f "$file.part"
        log ERROR "pg_dump failed"
        return 1
    fi
    find /backups -name 'prasibali-*.dump' -type f -mtime +"$KEEP_DAYS" -print -delete | while read -r old; do
        log INFO "Old backup deleted: $(basename "$old")"
    done
}

seconds_until() {
    # Seconds from now until the next HH:MM (local time).
    now=$(date +%s)
    target=$(date -d "$(date +%Y-%m-%d) $1" +%s 2>/dev/null || date -D '%Y-%m-%d %H:%M' -d "$(date +%Y-%m-%d) $1" +%s)
    if [ "$target" -le "$now" ]; then
        target=$((target + 86400))
    fi
    echo $((target - now))
}

if [ "${1:-}" = "now" ]; then
    dump
    exit $?
fi

log INFO "Backup service started: daily at $AT, keeping $KEEP_DAYS days"
while true; do
    sleep "$(seconds_until "$AT")"
    dump || true
done
