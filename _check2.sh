cd /opt/legal_mind

echo "=== Что в пакете yandexcloud ==="
sudo -u legal ./venv/bin/pip show -f yandexcloud | grep -i "lockbox\|^Name\|^Version" | head -20

echo ""
echo "=== Импорт напрямую ==="
sudo -u legal ./venv/bin/python -c "from yandex_cloud_ml_sdk import YCloudML; print('ml sdk есть')" 2>&1
sudo -u legal ./venv/bin/python -c "import yandex.cloud.lockbox.v1.lockbox_service_pb2_grpc" 2>&1 | head -3
sudo -u legal ./venv/bin/python -c "from yandexcloud._wrappers.lockbox import Lockbox" 2>&1 | head -3