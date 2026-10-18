// Demo-only controls. Only available when USE_MOCK is true.
import { mock } from "../mock/db";

export const devApi = {
  simulateNewTickets: () => mock.simulateNewTickets(2),
  simulateReporterReply: () => mock.simulateReporterReply(),
  simulateShipSync: () => mock.simulateShipSync(),
  reset: () => mock.reset(),
};
