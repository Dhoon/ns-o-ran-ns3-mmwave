#!/usr/bin/env bash
echo "===== [A] e2term 로그 (gnb 필터) — Ctrl+C로 보기 중단 ====="
docker logs e2term -f --since=1s 2>&1 | grep --line-buffered gnb:
echo "(e2term 로그 종료. RIC 안 떠있으면 'docker ps'로 확인)"
exec bash
