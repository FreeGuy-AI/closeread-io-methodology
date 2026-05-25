---
finding_category: credentials
severity_observed: high
remediation_effort: S
detection_method: deterministic
anonymized: true
contributed_by: free-guy-internal
source_audit: 2026-05-22-batch (anonymized; 4/10 incidence)
---

# Secret baked into Docker image via `ARG` or `ENV` at build time

## What the audit found

Four audits in the same batch of ten. Different stacks, different teams, different CI providers (GitHub Actions, GitLab CI, CircleCI, a self-hosted Jenkins). The same pattern in every one: a `Dockerfile` (or a `docker-compose.yml`, or a Kubernetes manifest at the image-build layer) that passed a credential as a build argument and embedded it into the resulting image either through an `ENV` directive or through a layer that included the secret in a `RUN` command's output.

The variations were instructive:

- One repo had `ARG NPM_TOKEN` at the top of the Dockerfile, used `RUN npm install --token=$NPM_TOKEN` to authenticate against a private npm registry, and then never removed the token. The token remained in the layer metadata, recoverable to anyone who pulled the image and ran `docker history --no-trunc`.
- One repo set `ENV DATABASE_URL=postgresql://app:hunter2@db.internal:5432/prod` directly in the Dockerfile to "simplify local development." The image was pushed to a public Docker Hub repository under the team's namespace. The credentials were valid against the production database for nine months before the audit found them.
- One repo passed a Stripe live secret key as a build argument in the GitHub Actions workflow (`--build-arg STRIPE_SECRET=${{ secrets.STRIPE_SECRET }}`), expecting the secret to disappear after the build. The build step's `RUN` command echoed the argument into a startup script written to `/app/start.sh`, which baked the literal secret into the final image. The secret was visible in `docker history` of every published image tag.
- One repo used a multi-stage Dockerfile where the build stage cloned a private GitHub repo using a deploy token passed as `ARG GH_TOKEN`. The runtime stage did not copy the token, but the build stage's image was also pushed (mistakenly) and the token was recoverable from its layer history. The token had `repo` scope across the entire organization.

In all four cases the seller believed the image was clean either because the secret "was a build argument, not a runtime variable" or because "the secret is not in the final stage" or because "no one would dig into the image layers." In all four cases the audit recovered the secret with a single `docker history --no-trunc` or `docker inspect` invocation.

## How the audit caught it

The credentials specialist runs three passes against container artifacts.

The Dockerfile static pass walks every `Dockerfile`, `Containerfile`, and equivalent in the repository. Findings fire on:

- `ENV` directives whose values match the credential regex set (AWS keys, Stripe keys, generic high-entropy `KEY=...` patterns).
- `ARG` directives consumed by `RUN` commands that write to disk or set environment variables in a layer.
- `RUN` commands containing literal credential patterns directly.
- `COPY` commands sourcing files that the secrets pass identifies as containing credentials.

Each match emits a HIGH finding with the line number and the credential pattern observed.

The compose static pass walks `docker-compose.yml`, `docker-compose.*.yml`, and Kubernetes manifests for `environment:` blocks containing the same credential patterns. The same HIGH rules apply.

The image dynamic pass, when the deep audit includes pulling published images, runs `docker pull` against any tagged image referenced in the repository's documentation or CI workflows and then runs `docker history --no-trunc` and `docker inspect` on each. A credential pattern found in any layer's history (even one that does not appear in the runtime filesystem) emits a HIGH finding. A credential found in the runtime filesystem (extracted via `docker save | tar -xf -` and a recursive grep of the layer tarballs) emits a CRITICAL finding because the secret is reachable to any container the image runs as.

## Why it matters to a buyer

Three reasons, in ascending order of cost.

First, the image is shipped, not built. Docker images are designed to be portable artifacts. Every customer pull, every CI cache, every developer laptop that ever ran the image holds a full copy of every layer including any baked-in secret. Rotating the secret after the audit closes the live exposure but does not retrieve the secret from any of those locations. The seller is in the same epistemological position as with a leaked git history: the secret is recoverable by parties the seller cannot enumerate, for as long as those parties retain the image.

Second, the public-registry escalation. Two of the four cases in this batch involved images pushed to public registries (Docker Hub in both cases). A public registry secret leak is functionally identical to a public git-history leak: it is indexable, scrapable, and incorporated into public credential-scanning datasets within hours of being pushed. The seller in one of the two cases received an automated GitHub Secret Scanning notification six weeks after the original push and rotated reactively; the seller in the other case did not know until the audit.

Third, the cultural signal. Build-time credential leakage is one of the cleanest signals available that the seller's CI architecture treats credentials as data to pass around rather than as secrets to inject at runtime. Buyers' diligence teams read the finding as evidence of broader credential-hygiene gaps and will probe other surfaces (runtime environment variables, log payloads, error-reporting integrations) for the same class. Realistic dollar impact: $5K to $20K of engineering work to rebuild the credential-injection architecture, plus the rotation cost of every credential ever baked into a published image, plus any cost from public-registry exposure that surfaces during diligence.

## Recommended remediation

In order, all of these need to happen:

1. **Rotate every credential that was ever passed as a build argument or baked into an image.** Assume compromise from the day of the first build that included the secret. This includes registry tokens, deploy tokens, database credentials, third-party API keys, and any value whose presence in the image layers was confirmed by the audit.
2. **Remove the `ARG` and `ENV` patterns from the Dockerfile.** Replace with runtime injection: environment variables passed by the orchestrator (Kubernetes secret references, ECS task definitions, Docker Swarm secrets, plain `docker run -e KEY=$VALUE` from a CI step), volume-mounted secret files, or a runtime call to a secrets manager (Vault, AWS Secrets Manager, GCP Secret Manager, 1Password Connect).
3. **For genuinely build-time-required secrets (private package installs, private repo clones), use Docker BuildKit secret mounts.** `--mount=type=secret,id=npm_token` provides the secret to the build step without writing it to any layer. The secret is unmounted before the layer is committed. This is the only safe pattern for build-time secrets.
4. **Rebuild and republish every affected image tag.** The old tags must be deleted from the registry (this is the only way to break the link for new pulls) and replaced with rebuilt versions that do not contain the secret. Old caches at customer sites are unrecoverable; the rotation in step 1 is the only defense against those.
5. **Add a CI scan.** `trivy image`, `dockle`, or the `docker scout` toolchain can scan an image for embedded secrets as part of the build pipeline. A failed scan on any new image build catches regressions before the image reaches a registry.

## How the seller could have prevented this

The structural prevention is BuildKit secret mounts from day one for any build-time credential need, combined with runtime injection (Kubernetes secrets, ECS task definitions, or an external secrets manager) for any runtime credential need. The Dockerfile never contains a credential pattern, the image never contains a credential layer, and the audit never finds a credential to flag.

The behavioral prevention, for teams that have not yet migrated to BuildKit secret mounts, is a CI-side scan on every image push (`trivy image --severity HIGH,CRITICAL --exit-code 1 ...`) that fails the build if any credential pattern matches in any layer. The scan catches the leak at CI time, before the image reaches the registry and gets pulled by customers.

The seller who has done neither faces a multi-day remediation cycle: rotate every credential, rebuild every image, force-delete every old tag from every registry, and hope that no customer pulled the bad image and incorporated it into a downstream artifact. The seller who has done the structural prevention arrives at exit with a clean image-credential finding, a documented runtime-injection architecture, and one fewer high-severity finding in the buyer's diligence report.
