import { USE_MOCK } from "../config";
import { request } from "../client";
import { mock } from "../mock/db";
import type { LoginResponse } from "../types";

// POST /auth/login
export function login(email: string, password: string): Promise<LoginResponse> {
  return USE_MOCK ? mock.login(email, password) : request("POST", "/auth/login", { body: { email, password } });
}
