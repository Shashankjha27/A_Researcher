export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

async function parseError(res: Response): Promise<never> {
  let detail = `${res.status} ${res.statusText}`

  try {
    const body = (await res.json()) as { detail?: unknown }

    if (body?.detail) {
      detail =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail)
    }
  } catch {
    // keep status text fallback
  }

  throw new ApiError(detail, res.status)
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)

  if (!res.ok) {
    return parseError(res)
  }

  if (res.status === 204) {
    return undefined as T
  }

  return (await res.json()) as T
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path)
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: "POST",
      headers:
        body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  },
  postForm<T>(path: string, form: FormData): Promise<T> {
    return request<T>(path, { method: "POST", body: form })
  },
  del<T>(path: string): Promise<T> {
    return request<T>(path, { method: "DELETE" })
  },
}
