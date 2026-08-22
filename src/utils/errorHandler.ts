export interface AppError {
  message: string;
  code?: string | number;
  details?: unknown;
}

/**
 * Centralized exception handler to format errors consistently and provide meaningful feedback.
 */
export function handleAppException(error: unknown, fallbackMessage: string = "An unexpected error occurred."): AppError {
  console.error("[EcoBuddy Error]:", error);

  if (error instanceof Error) {
    return {
      message: error.message || fallbackMessage,
      details: error.stack,
    };
  }

  if (typeof error === "string") {
    return {
      message: error,
    };
  }

  return {
    message: fallbackMessage,
    details: error,
  };
}

/**
 * Higher-order wrapper for async functions to catch and handle exceptions seamlessly.
 */
async function withErrorHandler<T>(
  asyncFn: () => Promise<T>,
  fallbackMessage?: string
): Promise<[T | null, AppError | null]> {
  try {
    const data = await asyncFn();
    return [data, null];
  } catch (error) {
    const formattedError = handleAppException(error, fallbackMessage);
    return [null, formattedError];
  }
}
