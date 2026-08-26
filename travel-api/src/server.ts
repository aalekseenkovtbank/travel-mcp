import { createServer } from "node:http";

import { createApp } from "./app.js";
import { env } from "./config/env.js";
import { createRuntime } from "./runtime.js";

const runtime = createRuntime();
const app = createApp(runtime);
const server = createServer(app);

server.listen(env.PORT, env.HOST, () => {
  console.log(
    JSON.stringify({
      level: "info",
      message: "Travel Nova API started",
      url: `http://${env.HOST}:${env.PORT}`,
      environment: env.NODE_ENV,
    }),
  );
});

function shutdown(signal: NodeJS.Signals): void {
  console.log(JSON.stringify({ level: "info", message: "Shutting down", signal }));

  server.close(async (error) => {
    if (error) {
      console.error(JSON.stringify({ level: "error", message: error.message }));
      process.exitCode = 1;
    }
    await runtime.close();
  });
}

process.once("SIGINT", shutdown);
process.once("SIGTERM", shutdown);
