// === Accounts ===

export interface TokenStatus {
  is_logged_in: boolean;
  login_time: string | null;
  expires_at: string | null;
}

export interface Account {
  id: string;
  name: string;
  owner_name: string | null;
  has_kite_credentials: boolean;
  is_active: boolean;
  max_lots: number;
  token_status: TokenStatus;
  created_at: string;
  updated_at: string;
}

export interface AccountCreate {
  name: string;
  owner_name?: string;
  kite_api_key?: string;
  kite_api_secret?: string;
  max_lots: number;
}

export interface AccountUpdate {
  name?: string;
  owner_name?: string;
  kite_api_key?: string;
  kite_api_secret?: string;
  is_active?: boolean;
  max_lots?: number;
}

export interface AuthStatus {
  account_id: string;
  name: string;
  is_logged_in: boolean;
  login_time: string | null;
  expires_at: string | null;
}

export interface LoginUrlResponse {
  login_url: string;
  account_id: string;
}

// === Orders ===

export interface OrderParams {
  exchange: string;
  tradingsymbol: string;
  transaction_type: "BUY" | "SELL";
  order_type: "MARKET" | "LIMIT" | "SL" | "SL-M";
  product: "NRML" | "MIS" | "CNC";
  variety?: string;
  price?: number;
  trigger_price?: number;
}

export interface PlaceOrderRequest {
  account_ids: string[];
  mode: "uniform" | "custom";
  order: OrderParams;
  uniform_quantity?: number;
  custom_allocations?: Record<string, number>;
}

export interface PlaceOrderResult {
  account_id: string;
  account_name: string;
  order_id: string | null;
  kite_order_id: string | null;
  status: string;
  message: string | null;
}

export interface PlaceOrderResponse {
  group_id: string;
  results: PlaceOrderResult[];
  total: number;
  placed: number;
  failed: number;
}

export interface OrderItem {
  id: string;
  account_id: string;
  account_name: string | null;
  group_id: string | null;
  kite_order_id: string | null;
  exchange: string;
  tradingsymbol: string;
  transaction_type: string;
  order_type: string;
  product: string;
  variety: string;
  quantity: number;
  price: number | null;
  trigger_price: number | null;
  filled_quantity: number;
  average_price: number | null;
  status: string;
  status_message: string | null;
  placed_at: string | null;
  created_at: string;
}

export interface InstrumentResult {
  tradingsymbol: string;
  exchange: string;
  instrument_type: string;
  name: string;
  lot_size: number;
  expiry: string | null;
  strike: number | null;
  tick_size: number;
}

// === WebSocket ===

export interface OrderUpdate {
  order_id: string;
  account_id: string;
  account_name: string;
  kite_order_id: string;
  tradingsymbol: string;
  old_status: string;
  new_status: string;
  filled_quantity: number;
  average_price: number | null;
}
