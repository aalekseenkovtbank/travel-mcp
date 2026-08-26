import type {
  DiningProfile,
  IncomeCohort,
  ShoppingProfile,
  SpendingCategoryProfile,
} from "@travel-growth-inspiration/contracts";

export type ProfileOperation = {
  id: string;
  occurredAt: string;
  type: string;
  amount?: number | string | null;
  currency: string;
  description: string;
  category?: string;
};

export type CategoryAggregate = {
  name: string;
  amount: number;
};

export type TransactionProfile = {
  transactionCount: number;
  estimatedMonthlyIncomeRub: number;
  incomeCohort: IncomeCohort;
  incomeConfidence: "unavailable" | "low" | "medium" | "high";
  weekendAverageDailySpendRub: number;
  weekdayAverageDailySpendRub: number;
  weekendSpendSharePct: number;
  averageCheckRub: number;
  medianCheckRub: number;
  categoryBreakdown: SpendingCategoryProfile[];
  diningProfile: DiningProfile;
  shoppingProfile: ShoppingProfile;
  llmSummary: string;
};

const DINING_PATTERN = /ресторан|кафе|кофе|бар|паб|фастфуд|еда|столов|restaurant|cafe|coffee|bar|pub|fast.?food|dining/iu;
const SHOPPING_PATTERN = /магазин|супермаркет|продукт|одежд|обув|аптек|электроник|товары для дома|market|grocery|supermarket|shop|retail|pharmacy/iu;
const SALARY_PATTERN = /зарплат|аванс|salary|payroll/iu;

const CUISINES: Array<[string, RegExp]> = [
  ["японская", /суш|ролл|рамен|япон|sushi|ramen|japan/iu],
  ["итальянская", /пицц|паст|итальян|pizza|pasta|italian/iu],
  ["грузинская", /хинкал|хачапур|грузин|georgian/iu],
  ["азиатская", /вок|паназиат|азиат|тайск|китай|корей|wok|asian|thai|china|korean/iu],
  ["кавказская", /кавказ|шашлык|мангал|caucas/iu],
  ["русская", /русск.*кух|пельмен|блин|russian/iu],
  ["мексиканская", /тако|буррит|мексик|taco|burrito|mexican/iu],
  ["американская", /бургер|burger|american/iu],
  ["вегетарианская", /веган|вегетариан|vegan|vegetarian/iu],
];

const DINING_VENUES: Array<[string, RegExp]> = [
  ["кафе и кофейни", /кафе|кофе|cafe|coffee/iu],
  ["бары и пабы", /бар|паб|bar|pub/iu],
  ["фастфуд", /фастфуд|бургер|шаурм|fast.?food|burger/iu],
  ["рестораны", /ресторан|restaurant/iu],
  ["столовые", /столов|canteen/iu],
];

const STORE_TYPES: Array<[string, RegExp]> = [
  ["продукты и супермаркеты", /продукт|супермаркет|grocery|supermarket|market/iu],
  ["аптеки", /аптек|pharmacy/iu],
  ["одежда и обувь", /одежд|обув|fashion|clothes|shoe/iu],
  ["электроника", /электроник|техник|electronics/iu],
  ["товары для дома", /товары для дома|мебел|home|furniture/iu],
];

function numeric(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(String(value ?? "").replace(",", "."));
  return Number.isFinite(parsed) ? parsed : 0;
}

function normalized(value: string): string {
  return value.toLocaleLowerCase("ru").replace(/\s+/gu, " ").trim();
}

function isRub(currency: string): boolean {
  return !currency || /rub|руб|₽|643/iu.test(currency);
}

function isDebit(operation: ProfileOperation): boolean {
  return normalized(operation.type) === "debit" && isRub(operation.currency);
}

function isCredit(operation: ProfileOperation): boolean {
  return normalized(operation.type) === "credit" && isRub(operation.currency);
}

function amountOf(operation: ProfileOperation): number {
  return Math.abs(numeric(operation.amount));
}

function categoryKey(value: string | undefined): string {
  return normalized(value ?? "Без категории");
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? ((sorted[middle - 1] ?? 0) + (sorted[middle] ?? 0)) / 2
    : (sorted[middle] ?? 0);
}

function average(values: number[]): number {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
}

function round(value: number): number {
  return Math.max(0, Math.round(value));
}

function roundPct(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value * 10) / 10));
}

function dateOnly(value: string): string | undefined {
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})/u);
  return match ? `${match[1]}-${match[2]}-${match[3]}` : undefined;
}

function isWeekend(date: string): boolean {
  const [year, month, day] = date.split("-").map(Number);
  const weekday = new Date(Date.UTC(year ?? 0, (month ?? 1) - 1, day ?? 1)).getUTCDay();
  return weekday === 0 || weekday === 6;
}

function calendarDayCounts(windowDays: number, nowMs: number): { weekend: number; weekday: number } {
  // T-Bank serializes operation dates in Moscow time; use the same calendar boundary.
  const end = new Date(nowMs + 3 * 60 * 60_000);
  const cursor = new Date(Date.UTC(end.getUTCFullYear(), end.getUTCMonth(), end.getUTCDate()));
  let weekend = 0;
  let weekday = 0;
  for (let offset = 0; offset < windowDays; offset += 1) {
    const date = cursor.toISOString().slice(0, 10);
    if (isWeekend(date)) weekend += 1;
    else weekday += 1;
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return { weekend, weekday };
}

function rankSignals(
  operations: ProfileOperation[],
  patterns: Array<[string, RegExp]>,
  fallback?: string,
): string[] {
  const scores = new Map<string, number>();
  for (const operation of operations) {
    const text = `${operation.category ?? ""} ${operation.description}`;
    let matched = false;
    for (const [label, pattern] of patterns) {
      if (!pattern.test(text)) continue;
      scores.set(label, (scores.get(label) ?? 0) + 1);
      matched = true;
    }
    if (!matched && fallback) scores.set(fallback, (scores.get(fallback) ?? 0) + 1);
  }
  return [...scores.entries()]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0], "ru"))
    .map(([label]) => label);
}

export function incomeCohort(monthlyIncomeRub: number): IncomeCohort {
  if (monthlyIncomeRub <= 0) return "unknown";
  if (monthlyIncomeRub <= 50_000) return "up_to_50k";
  if (monthlyIncomeRub <= 100_000) return "50k_to_100k";
  if (monthlyIncomeRub <= 200_000) return "100k_to_200k";
  if (monthlyIncomeRub <= 500_000) return "200k_to_500k";
  if (monthlyIncomeRub <= 1_000_000) return "500k_to_1m";
  return "1m_plus";
}

export function incomeCohortLabel(cohort: IncomeCohort): string {
  const labels: Record<IncomeCohort, string> = {
    unknown: "доход не определён",
    up_to_50k: "до 50 тыс. ₽/мес.",
    "50k_to_100k": "50–100 тыс. ₽/мес.",
    "100k_to_200k": "100–200 тыс. ₽/мес.",
    "200k_to_500k": "200–500 тыс. ₽/мес.",
    "500k_to_1m": "500 тыс.–1 млн ₽/мес.",
    "1m_plus": "от 1 млн ₽/мес.",
  };
  return labels[cohort];
}

export function buildTransactionProfile(input: {
  operations: ProfileOperation[];
  categoryAggregates: CategoryAggregate[];
  totalSpent90Rub: number;
  totalEarned90Rub: number;
  analysisWindowDays?: number;
  completeAccounts: boolean;
  nowMs?: number;
}): TransactionProfile {
  const analysisWindowDays = input.analysisWindowDays ?? 90;
  const seenOperationIds = new Set<string>();
  const uniqueOperations = input.operations.filter((operation) => {
    if (!operation.id) return true;
    if (seenOperationIds.has(operation.id)) return false;
    seenOperationIds.add(operation.id);
    return true;
  });
  const debits = uniqueOperations.filter(isDebit).filter((operation) => amountOf(operation) > 0);
  const credits = uniqueOperations.filter(isCredit).filter((operation) => amountOf(operation) > 0);
  const checks = debits.map(amountOf);
  const dayCounts = calendarDayCounts(analysisWindowDays, input.nowMs ?? Date.now());
  let weekendSpend = 0;
  let weekdaySpend = 0;
  for (const operation of debits) {
    const date = dateOnly(operation.occurredAt);
    if (!date) continue;
    if (isWeekend(date)) weekendSpend += amountOf(operation);
    else weekdaySpend += amountOf(operation);
  }

  const salaryByMonth = new Map<string, number>();
  for (const operation of credits) {
    if (!SALARY_PATTERN.test(operation.description)) continue;
    const month = dateOnly(operation.occurredAt)?.slice(0, 7);
    if (month) salaryByMonth.set(month, (salaryByMonth.get(month) ?? 0) + amountOf(operation));
  }
  const salaryMonths = [...salaryByMonth.values()];
  const aggregateMonthlyIncome = round(input.totalEarned90Rub * 30 / analysisWindowDays);
  const estimatedMonthlyIncomeRub = salaryMonths.length >= 2
    ? round(median(salaryMonths))
    : aggregateMonthlyIncome;
  const cohort = incomeCohort(estimatedMonthlyIncomeRub);
  const incomeConfidence: TransactionProfile["incomeConfidence"] = estimatedMonthlyIncomeRub <= 0
    ? "unavailable"
    : salaryMonths.length >= 2 && input.completeAccounts
      ? "high"
      : input.completeAccounts
        ? "medium"
        : "low";

  const aggregateByKey = new Map<string, { name: string; amount: number }>();
  for (const category of input.categoryAggregates) {
    const key = categoryKey(category.name);
    const previous = aggregateByKey.get(key);
    aggregateByKey.set(key, {
      name: previous?.name ?? (category.name.trim() || "Без категории"),
      amount: (previous?.amount ?? 0) + Math.max(0, category.amount),
    });
  }
  const checksByCategory = new Map<string, number[]>();
  for (const operation of debits) {
    const key = categoryKey(operation.category);
    const values = checksByCategory.get(key) ?? [];
    values.push(amountOf(operation));
    checksByCategory.set(key, values);
  }
  const totalCategorySpend = [...aggregateByKey.values()].reduce((sum, category) => sum + category.amount, 0)
    || input.totalSpent90Rub;
  const categoryBreakdown: SpendingCategoryProfile[] = [...aggregateByKey.entries()]
    .sort((left, right) => right[1].amount - left[1].amount)
    .slice(0, 10)
    .map(([key, category]) => {
      const categoryChecks = checksByCategory.get(key) ?? [];
      return {
        name: category.name,
        monthlySpendRub: round(category.amount * 30 / analysisWindowDays),
        sharePct: roundPct(totalCategorySpend > 0 ? category.amount / totalCategorySpend * 100 : 0),
        averageCheckRub: round(average(categoryChecks)),
        transactionCount: categoryChecks.length,
      };
    });

  const diningOperations = debits.filter((operation) =>
    DINING_PATTERN.test(`${operation.category ?? ""} ${operation.description}`));
  const shoppingOperations = debits.filter((operation) =>
    SHOPPING_PATTERN.test(`${operation.category ?? ""} ${operation.description}`));
  const diningChecks = diningOperations.map(amountOf);
  const shoppingChecks = shoppingOperations.map(amountOf);
  const diningProfile: DiningProfile = {
    averageCheckRub: round(average(diningChecks)),
    medianCheckRub: round(median(diningChecks)),
    preferredCuisines: rankSignals(diningOperations, CUISINES).slice(0, 5),
    preferredVenueTypes: rankSignals(diningOperations, DINING_VENUES, "рестораны").slice(0, 4),
  };
  const shoppingProfile: ShoppingProfile = {
    averageCheckRub: round(average(shoppingChecks)),
    medianCheckRub: round(median(shoppingChecks)),
    preferredStoreTypes: rankSignals(shoppingOperations, STORE_TYPES, "другие магазины").slice(0, 5),
  };

  const weekendAverageDailySpendRub = round(weekendSpend / Math.max(1, dayCounts.weekend));
  const weekdayAverageDailySpendRub = round(weekdaySpend / Math.max(1, dayCounts.weekday));
  const observedSpend = weekendSpend + weekdaySpend;
  const weekendSpendSharePct = roundPct(observedSpend > 0 ? weekendSpend / observedSpend * 100 : 0);
  const topCategories = categoryBreakdown.slice(0, 3).map((category) => category.name).join(", ");
  const diningSignals = [...diningProfile.preferredVenueTypes, ...diningProfile.preferredCuisines]
    .slice(0, 4)
    .join(", ");
  const confidenceLabel = {
    unavailable: "нет оценки",
    low: "низкая уверенность",
    medium: "средняя уверенность",
    high: "высокая уверенность",
  }[incomeConfidence];
  const llmSummary = [
    `Доходная когорта: ${incomeCohortLabel(cohort)} (${confidenceLabel}).`,
    `Средние траты: ${round(input.totalSpent90Rub * 30 / analysisWindowDays).toLocaleString("ru-RU")} ₽/мес.; выходной день: ${weekendAverageDailySpendRub.toLocaleString("ru-RU")} ₽; обычный день: ${weekdayAverageDailySpendRub.toLocaleString("ru-RU")} ₽.`,
    `Типичный чек: ${round(median(checks)).toLocaleString("ru-RU")} ₽ (средний ${round(average(checks)).toLocaleString("ru-RU")} ₽).`,
    ...(topCategories ? [`Основные категории: ${topCategories}.`] : []),
    ...(diningChecks.length ? [`Еда вне дома: средний чек ${diningProfile.averageCheckRub.toLocaleString("ru-RU")} ₽${diningSignals ? `; чаще: ${diningSignals}` : ""}.`] : []),
  ].join(" ");

  return {
    transactionCount: debits.length,
    estimatedMonthlyIncomeRub,
    incomeCohort: cohort,
    incomeConfidence,
    weekendAverageDailySpendRub,
    weekdayAverageDailySpendRub,
    weekendSpendSharePct,
    averageCheckRub: round(average(checks)),
    medianCheckRub: round(median(checks)),
    categoryBreakdown,
    diningProfile,
    shoppingProfile,
    llmSummary,
  };
}
