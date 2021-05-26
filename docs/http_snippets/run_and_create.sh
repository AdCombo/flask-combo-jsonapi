#!/usr/bin/env sh

echo "Create HTTP snippets"
httpsnippet ./*.json  --target http --output ./snippets

echo "Create Python (requests) snippets"
httpsnippet ./*.json --target python --client requests --output ./snippets

echo "Run requests"
python3 update_snippets_with_responses.py
