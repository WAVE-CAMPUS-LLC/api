import os
import textwrap

branches = {
    "v1_waveProduction": {
        "secret": "DISCORD_V1_PRODUCTION_WEBHOOK_URL",
        "color": 3073599  # Blue
    },
    "vm1_waveMobileProduction": {
        "secret": "DISCORD_VM1_MOBILE_PRODUCTION_WEBHOOK_URL",
        "color": 16753920  # Orange
    },
    "v1_apiOptimizationMain": {
        "secret": "DISCORD_V1_API_OPTIMIZATION_WEBHOOK_URL",
        "color": 3066993  # Green
    },
    "vm1_waveMobileDevelopment": {
        "secret": "DISCORD_VM1_MOBILE_DEVELOPMENT_WEBHOOK_URL",
        "color": 3066993  # Green
    }
}

template = textwrap.dedent(r"""\
    name: Notify Discord on Push to {branch}

    on:
      push:
        branches:
          - {branch}

    jobs:
      notify:
        runs-on: ubuntu-latest
        steps:
          - name: Send rich embed to Discord
            env:
              DISCORD_WEBHOOK_URL: ${{{{ secrets.{secret} }}}}
            run: |
              COMMITS=$(echo '${{{{ toJson(github.event.commits) }}}}' | jq -r '.[] | "- [`\\(.id[0:7])`](\\(.url)) by \\(.author.name): \\(.message | gsub("`"; "\\\\`") | gsub("\\*"; "\\\\*") | gsub("\""; "\\\\\""))"')
              COMMIT_COUNT=$(echo "$COMMITS" | wc -l)
              COMMIT_LIST=$(echo "$COMMITS" | sed ':a;N;$!ba;s/\n/\\n/g')
              REPO="${{{{ github.repository }}}}"
              BRANCH="{branch}"
              curl -H "Content-Type: application/json" \
                -X POST \
                -d "{{
                  \"embeds\": [{{
                    \"title\": \"🚀 Push to $BRANCH\",
                    \"description\": \"**$COMMIT_COUNT commit(s)** pushed to `$BRANCH` in [$REPO](https://github.com/$REPO):\\n$COMMIT_LIST\",
                    \"color\": {color},
                    \"footer\": {{
                      \"text\": \"GitHub Actions • $(date -u +\"%Y-%m-%d %H:%M:%S UTC\")\"
                    }}
                  }}]
                }}" \
                $DISCORD_WEBHOOK_URL
""")

for branch, data in branches.items():
    filename = f".github/workflows/discord-notify-{branch}.yml"
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:  # ✅ FIX: UTF-8 encoding
        f.write(template.format(branch=branch, secret=data["secret"], color=data["color"]))

    print(f"✅ Generated {filename}")
