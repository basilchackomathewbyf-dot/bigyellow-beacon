import { API_BASE_URL } from "./config";
import { authStore } from "@/lib/auth-store";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | string[] | number[] | undefined>;

function buildUrl(path: string, query?: Query) {
  const base = API_BASE_URL.replace(/\/+$/, "");
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const full = `${base}${cleanPath}`;
  let url: URL;
  if (full.startsWith("http://") || full.startsWith("https://")) {
    url = new URL(full);
  } else {
    const origin =
      typeof window !== "undefined"
        ? window.location.origin
        : (typeof process !== "undefined" && process.env?.INTERNAL_ORIGIN) || "http://127.0.0.1";
    url = new URL(full, origin);
  }
  if (query) {
    for (const [k, v] of Object.entries(query)) {
      if (v === undefined || v === "") continue;
      if (Array.isArray(v)) v.forEach((x) => url.searchParams.append(k, String(x)));
      else url.searchParams.set(k, String(v));
    }
  }
  return url.toString();
}

export async function request<T>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  opts: { body?: unknown; query?: Query; form?: FormData } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = authStore.getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";

  const res = await fetch(buildUrl(path, opts.query), {
    method,
    headers,
    body: opts.form ?? (opts.body !== undefined ? JSON.stringify(opts.body) : undefined),
  });

  if (res.status === 401) {
    const text = await res.text();
    let data;
    try {
      data = text ? JSON.parse(text) : undefined;
    } catch {
      data = undefined;
    }
    const errorMsg =
      data?.detail?.error ??
      data?.error ??
      data?.message ??
      (typeof data?.detail === "string" ? data.detail : "Unauthorized");

    if (!path.includes("/auth/login")) {
      authStore.clear();
      if (typeof window !== "undefined") window.location.assign("/login");
    }
    throw new ApiError(401, errorMsg, data);
  }

  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : undefined;
  } catch {
    data = undefined;
  }

  if (!res.ok) {
    const errorMsg =
      data?.detail?.error ??
      data?.message ??
      data?.error ??
      (typeof data?.detail === "string" ? data.detail : undefined) ??
      res.statusText;
    throw new ApiError(res.status, errorMsg, data);
  }
  return data as T;
}
