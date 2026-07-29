# Target Artifact Layout

Keep every process artifact and result below one normalized target-domain root:

```text
output/{domain}/
|-- artifact-manifest.json
|-- recon/                 # DNS, subdomains, exposure probes, source-leak leads
|-- assets/
|   |-- js/                # Downloaded JavaScript and the JS URL inventory
|   |-- sourcemaps/        # Downloaded source maps
|   `-- screenshots/       # Browser and evidence screenshots
|-- analysis/              # Endpoint models, hypotheses, rankings, and probe plans
|-- evidence/              # Request/response results, linkage results, and verification
|-- reports/               # Final verifier-only reports
`-- runtime/
    |-- scripts/           # Target-specific helper scripts
    |-- logs/              # Tool execution logs
    `-- queue/              # Queue exports and worker artifacts
```

Use only the normalized hostname for `{domain}`. Ignore the URL scheme, port,
path, fragment, and query when selecting the root. For example,
`https://Example.com:8443/app?a=1` belongs to `output/example.com/`.

Never write target artifacts beside the repository source, directly under
`output/`, or into a legacy `downloaded/` or `findings/` directory. Classify a
file by what it represents:

- discovery observations go to `recon/`
- collected target files go to `assets/`
- derived models and plans go to `analysis/`
- executed-test proof and verifier state go to `evidence/`
- user-facing deliverables go to `reports/`
- disposable execution support goes to `runtime/`
