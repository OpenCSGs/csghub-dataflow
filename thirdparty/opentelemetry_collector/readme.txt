docker run -p 4317:4317 \
    -v /Users/lipeng/workspaces/git-devops/data-flow/thirdparty/opentelemetry_collector/otel-collector-config.yaml:/etc/otel-collector-config.yaml \
    otel/opentelemetry-collector:latest \
    --config=/etc/otel-collector-config.yaml