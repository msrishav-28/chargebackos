export type DisputesSearch = {
  q?: string; merchant?: string; family?: string; category?: string; state?: string;
  review?: boolean; high?: boolean; page?: number;
};

export function validateQueueSearch(s: Record<string, unknown>): DisputesSearch {
  const filter = (value: unknown) => typeof value === "string" && value && value !== "all" ? value.slice(0, 200) : undefined;
  const page = Number(s.page);
  return {
    q: filter(s.q), merchant: filter(s.merchant), family: filter(s.family), category: filter(s.category), state: filter(s.state),
    review: s.review === "1" || s.review === true ? true : undefined,
    high: s.high === "1" || s.high === true ? true : undefined,
    page: Number.isSafeInteger(page) && page > 1 ? page : undefined,
  };
}
