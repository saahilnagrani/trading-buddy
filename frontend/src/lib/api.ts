import axios from "axios";
import type {
  Account,
  AccountCreate,
  AccountUpdate,
  AuthStatus,
  LoginUrlResponse,
  PlaceOrderRequest,
  PlaceOrderResponse,
  OrderItem,
  InstrumentResult,
} from "./types";

const api = axios.create({
  baseURL: (process.env.NEXT_PUBLIC_API_URL || "") + "/api",
});

// === Accounts ===

export async function getAccounts(): Promise<Account[]> {
  const { data } = await api.get<{ accounts: Account[] }>("/accounts");
  return data.accounts;
}

export async function createAccount(payload: AccountCreate): Promise<Account> {
  const { data } = await api.post<Account>("/accounts", payload);
  return data;
}

export async function updateAccount(
  id: string,
  payload: AccountUpdate
): Promise<Account> {
  const { data } = await api.put<Account>(`/accounts/${id}`, payload);
  return data;
}

export async function deleteAccount(id: string): Promise<void> {
  await api.delete(`/accounts/${id}`);
}

// === Auth ===

export async function getLoginUrl(
  accountId: string
): Promise<LoginUrlResponse> {
  const { data } = await api.get<LoginUrlResponse>(
    `/auth/login-url/${accountId}`
  );
  return data;
}

export async function getAuthStatus(): Promise<AuthStatus[]> {
  const { data } = await api.get<{ accounts: AuthStatus[] }>("/auth/status");
  return data.accounts;
}

// === Orders ===

export async function placeOrders(
  payload: PlaceOrderRequest
): Promise<PlaceOrderResponse> {
  const { data } = await api.post<PlaceOrderResponse>("/orders/place", payload);
  return data;
}

export async function getOrders(params?: {
  account_id?: string;
  group_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ orders: OrderItem[]; total: number }> {
  const { data } = await api.get<{ orders: OrderItem[]; total: number }>(
    "/orders",
    { params }
  );
  return data;
}

export async function getOrderGroup(
  groupId: string
): Promise<{ orders: OrderItem[]; total: number }> {
  const { data } = await api.get<{ orders: OrderItem[]; total: number }>(
    `/orders/group/${groupId}`
  );
  return data;
}

export async function cancelOrder(
  orderId: string
): Promise<{ status: string; message: string }> {
  const { data } = await api.put(`/orders/${orderId}/cancel`);
  return data;
}

export async function modifyOrder(
  orderId: string,
  payload: { price?: number; quantity?: number; trigger_price?: number }
): Promise<{ status: string; message: string }> {
  const { data } = await api.put(`/orders/${orderId}/modify`, payload);
  return data;
}

// === Instruments ===

export async function searchInstruments(
  q: string,
  exchange?: string
): Promise<InstrumentResult[]> {
  const { data } = await api.get<InstrumentResult[]>(
    "/orders/instruments/search",
    { params: { q, exchange } }
  );
  return data;
}
