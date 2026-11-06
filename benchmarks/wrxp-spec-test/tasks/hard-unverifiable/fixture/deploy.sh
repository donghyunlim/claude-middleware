#!/usr/bin/env bash
# 배포 스크립트 (운영 서버에서 실행)
set -euo pipefail
VERSION="$1"
echo "deploying $VERSION"
# TODO: 배포가 끝나면 #deploy 채널에 알림
