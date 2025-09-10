#!/usr/bin/env bash
# wait-for-redis.sh: Wait for Redis service to be available before starting dependent services

set -e

host="$1"
port="$2"
shift 2
cmd="$@"

until nc -z "$host" "$port"; do
  >&2 echo "Waiting for Redis at $host:$port to be ready..."
  sleep 1
done

>&2 echo "Redis at $host:$port is ready - starting service"
exec $cmd
