import { Container, getContainer } from "@cloudflare/containers";

export class WarframeMcpContainer extends Container {
  defaultPort = 8080;
  // Keep warm enough for ChatGPT connector handshakes.
  sleepAfter = "30m";
}

export default {
  async fetch(
    request: Request,
    env: { WARFRAME_MCP: DurableObjectNamespace },
  ): Promise<Response> {
    const container = getContainer(env.WARFRAME_MCP);
    return container.fetch(request);
  },
};
