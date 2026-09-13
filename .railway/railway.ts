// Railway Infrastructure as Code (IaC).
//
// Railway auto-detects the root `Dockerfile` (capital D) and its CMD, injects a
// `PORT` environment variable that the app reads, and gates deploys on the
// healthcheck below. Apply with:
//
//   railway login && railway link
//   railway config plan
//   railway config apply
//
// See https://docs.railway.com/infrastructure-as-code
import { defineRailway, project, service } from "railway/iac";

export default defineRailway(() => {
  const api = service("nine-bars", {
    healthcheck: "/healthz",
  });

  return project("9Bars", {
    resources: [api],
  });
});
