// **********************************************
// Use JavaScript to visualize responses: https://docs.requestly.com/general/api-client/scripts
// **********************************************
const body =
  typeof rq.response.body === "string"
    ? JSON.parse(rq.response.body)
    : rq.response.body;

if (body?.data?.access) {
  rq.environment.set("access_token", body.data.access);
}

if (body?.data?.refresh) {
  rq.environment.set("refresh_token", body.data.refresh);
}

