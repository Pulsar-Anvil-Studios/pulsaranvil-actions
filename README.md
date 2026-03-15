# pulsaranvil-actions

Shared GitHub Actions composite actions for PulsarAnvil CI/CD.

## Actions

| Action | Description |
|--------|-------------|
| `validate-pr-title` | Enforce Conventional Commits format on PR titles |
| `rust-check` | Rust fmt + clippy + tests with coverage + diff-coverage for PRs |
| `cargo-deploy` | Build Rust Lambda functions with cargo-lambda and deploy via CDK |
| `release` | Conventional Commits release: changelog, version bump, tag, GitHub Release |

## Usage

### validate-pr-title

```yaml
- uses: Pulsar-Anvil-Studios/pulsaranvil-actions/.github/actions/validate-pr-title@v1
```

### rust-check

```yaml
- uses: Pulsar-Anvil-Studios/pulsaranvil-actions/.github/actions/rust-check@v1
  with:
    github-app-id: ${{ secrets.APP_ID }}
    github-app-pem: ${{ secrets.APP_PEM }}
    pr-number: ${{ github.event.pull_request.number }}
    base-ref: origin/${{ github.base_ref }}
    coverage-threshold: "98"
```

### cargo-deploy

```yaml
- uses: Pulsar-Anvil-Studios/pulsaranvil-actions/.github/actions/cargo-deploy@v1
  with:
    environment: dev
    aws-role-arn: ${{ secrets.AWS_ROLE_ARN }}
    account-id: ${{ secrets.AWS_ACCOUNT_ID }}
    github-app-id: ${{ secrets.APP_ID }}
    github-app-pem: ${{ secrets.APP_PEM }}
```

### release

```yaml
- uses: Pulsar-Anvil-Studios/pulsaranvil-actions/.github/actions/release@v1
  with:
    github-app-id: ${{ secrets.APP_ID }}
    github-app-pem: ${{ secrets.APP_PEM }}
```
