type ApiErrorBody = {
  error?: { message?: string };
  detail?: string | Array<{ msg?: string }>;
};

export async function readApiError(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as ApiErrorBody;
    if (body.error?.message) {
      return body.error.message;
    }
    if (typeof body.detail === "string") {
      return body.detail;
    }
    const validationMessage = body.detail?.find((item) => item.msg)?.msg;
    return validationMessage ?? fallback;
  } catch {
    return fallback;
  }
}
