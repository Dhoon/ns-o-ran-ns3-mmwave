#!/usr/bin/env bash
echo "===== [B] xApp (live log) ====="
echo "기존 xApp 종료 후 재시작하여 이 창에 로그를 표시합니다..."
docker exec sample-xapp-24 pkill -f hw_xapp_main 2>/dev/null
sleep 1
docker exec -it sample-xapp-24 bash -lc "cd /home/sample-xapp && ./run_xapp.sh"
echo "(xApp 종료됨)"
exec bash