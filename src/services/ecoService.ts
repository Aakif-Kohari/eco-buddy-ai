import { handleAppException } from '../utils/errorHandler';

export async function fetchEcoAnalytics(endpoint: string) {
  try {
    const response = await fetch(endpoint);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch eco analytics: ${response.statusText} (Status: ${response.status})`);
    }

    const data = await response.json();
    return { data, error: null };
  } catch (error) {
    const appError = handleAppException(error, "Unable to load eco analytics data at this time. Please try again later.");
    return { data: null, error: appError };
  }
}
