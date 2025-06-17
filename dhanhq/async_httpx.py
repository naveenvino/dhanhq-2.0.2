import logging
import httpx
from json import dumps as json_dumps

class AsyncDhanhq:
    """Asynchronous variant of :class:`dhanhq.dhanhq` using ``httpx.AsyncClient``."""

    # Exchange constants
    NSE = "NSE_EQ"
    BSE = "BSE_EQ"
    CUR = "NSE_CURRENCY"
    MCX = "MCX_COMM"
    FNO = "NSE_FNO"
    NSE_FNO = "NSE_FNO"
    BSE_FNO = "BSE_FNO"
    INDEX = "IDX_I"

    # Transaction type
    BUY = "BUY"
    SELL = "SELL"

    # Product types
    CNC = "CNC"
    INTRA = "INTRADAY"
    MARGIN = "MARGIN"
    CO = "CO"
    BO = "BO"
    MTF = "MTF"

    # Order types
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    SL = "STOP_LOSS"
    SLM = "STOP_LOSS_MARKET"

    # Validity
    DAY = "DAY"
    IOC = "IOC"

    def __init__(self, client_id, access_token, disable_ssl: bool = False, session: httpx.AsyncClient | None = None):
        self.client_id = str(client_id)
        self.access_token = access_token
        self.base_url = "https://api.dhan.co/v2"
        self.timeout = 60
        self.header = {
            "access-token": access_token,
            "Content-type": "application/json",
            "Accept": "application/json",
        }
        self.disable_ssl = disable_ssl
        if session is None:
            self.session = httpx.AsyncClient(timeout=self.timeout, verify=not disable_ssl)
            self._session_owner = True
        else:
            self.session = session
            self._session_owner = False

    async def close(self):
        if self._session_owner:
            await self.session.aclose()

    async def _parse_response(self, response: httpx.Response):
        try:
            python_response = response.json()
            if response.status_code == 200:
                return {"status": "success", "remarks": "", "data": python_response}
            return {
                "status": "failure",
                "remarks": {
                    "error_code": python_response.get("errorCode"),
                    "error_type": python_response.get("errorType"),
                    "error_message": python_response.get("errorMessage"),
                },
                "data": python_response,
            }
        except Exception as e:  # pragma: no cover - defensive
            logging.warning("Exception in AsyncDhanhq>>_parse_response: %s", e)
            return {"status": "failure", "remarks": str(e), "data": ""}

    async def get_order_list(self):
        try:
            url = self.base_url + "/orders"
            resp = await self.session.get(url, headers=self.header)
            return await self._parse_response(resp)
        except Exception as e:  # pragma: no cover - defensive
            logging.error("Exception in AsyncDhanhq>>get_order_list : %s", e)
            return {"status": "failure", "remarks": str(e), "data": ""}

    async def get_order_by_id(self, order_id):
        try:
            url = self.base_url + f"/orders/{order_id}"
            resp = await self.session.get(url, headers=self.header)
            return await self._parse_response(resp)
        except Exception as e:  # pragma: no cover - defensive
            logging.error("Exception in AsyncDhanhq>>get_order_by_id : %s", e)
            return {"status": "failure", "remarks": str(e), "data": ""}

    async def place_order(
        self,
        security_id,
        exchange_segment,
        transaction_type,
        quantity,
        order_type,
        product_type,
        price,
        trigger_price=0,
        disclosed_quantity=0,
        after_market_order=False,
        validity="DAY",
        amo_time="OPEN",
        bo_profit_value=None,
        bo_stop_loss_Value=None,
        tag=None,
    ):
        try:
            url = self.base_url + "/orders"
            payload = {
                "dhanClientId": self.client_id,
                "transactionType": transaction_type.upper(),
                "exchangeSegment": exchange_segment.upper(),
                "productType": product_type.upper(),
                "orderType": order_type.upper(),
                "validity": validity.upper(),
                "securityId": security_id,
                "quantity": int(quantity),
                "disclosedQuantity": int(disclosed_quantity),
                "price": float(price),
                "afterMarketOrder": after_market_order,
                "boProfitValue": bo_profit_value,
                "boStopLossValue": bo_stop_loss_Value,
            }
            if tag:
                payload["correlationId"] = tag
            if after_market_order:
                if amo_time in ["PRE_OPEN", "OPEN", "OPEN_30", "OPEN_60"]:
                    payload["amoTime"] = amo_time
                else:
                    raise Exception("amo_time value must be ['PRE_OPEN','OPEN','OPEN_30','OPEN_60']")
            payload["triggerPrice"] = float(trigger_price) if trigger_price > 0 else 0.0
            resp = await self.session.post(url, headers=self.header, data=json_dumps(payload))
            return await self._parse_response(resp)
        except Exception as e:  # pragma: no cover - defensive
            logging.error("Exception in AsyncDhanhq>>place_order: %s", e)
            return {"status": "failure", "remarks": str(e), "data": ""}

    async def get_positions(self):
        try:
            url = self.base_url + "/positions"
            resp = await self.session.get(url, headers=self.header)
            return await self._parse_response(resp)
        except Exception as e:  # pragma: no cover - defensive
            logging.error("Exception in AsyncDhanhq>>get_positions: %s", e)
            return {"status": "failure", "remarks": str(e), "data": ""}

    async def intraday_minute_data(
        self,
        security_id,
        exchange_segment,
        instrument_type,
        from_date,
        to_date,
        interval=1,
    ):
        try:
            url = self.base_url + "/charts/intraday"
            if interval not in [1, 5, 15, 25, 60]:
                raise Exception("interval value must be ['1','5','15','25','60']")
            payload = json_dumps({
                "securityId": security_id,
                "exchangeSegment": exchange_segment,
                "instrument": instrument_type,
                "interval": interval,
                "fromDate": from_date,
                "toDate": to_date,
            })
            resp = await self.session.post(url, headers=self.header, data=payload)
            return await self._parse_response(resp)
        except Exception as e:  # pragma: no cover - defensive
            logging.error("Exception in AsyncDhanhq>>intraday_minute_data: %s", e)
            return {"status": "failure", "remarks": str(e), "data": ""}

    async def historical_daily_data(
        self,
        security_id,
        exchange_segment,
        instrument_type,
        from_date,
        to_date,
        expiry_code=0,
    ):
        try:
            url = self.base_url + "/charts/historical"
            if expiry_code not in [0, 1, 2, 3]:
                raise Exception("expiry_code value must be ['0','1','2','3']")
            payload = json_dumps({
                "securityId": security_id,
                "exchangeSegment": exchange_segment,
                "instrument": instrument_type,
                "expiryCode": expiry_code,
                "fromDate": from_date,
                "toDate": to_date,
            })
            resp = await self.session.post(url, headers=self.header, data=payload)
            return await self._parse_response(resp)
        except Exception as e:  # pragma: no cover - defensive
            logging.error("Exception in AsyncDhanhq>>historical_daily_data: %s", e)
            return {"status": "failure", "remarks": str(e), "data": ""}

    async def ticker_data(self, securities):
        try:
            url = self.base_url + "/marketfeed/ltp"
            payload = json_dumps({k: v for k, v in securities.items()})
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "access-token": self.access_token,
                "client-id": self.client_id,
            }
            resp = await self.session.post(url, headers=headers, data=payload)
            return await self._parse_response(resp)
        except Exception as e:  # pragma: no cover - defensive
            logging.error("Exception in AsyncDhanhq>>ticker_data: %s", e)
            return {"status": "failure", "remarks": str(e), "data": ""}

    async def ohlc_data(self, securities):
        try:
            url = self.base_url + "/marketfeed/ohlc"
            payload = json_dumps({k: v for k, v in securities.items()})
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "access-token": self.access_token,
                "client-id": self.client_id,
            }
            resp = await self.session.post(url, headers=headers, data=payload)
            return await self._parse_response(resp)
        except Exception as e:  # pragma: no cover - defensive
            logging.error("Exception in AsyncDhanhq>>ohlc_data: %s", e)
            return {"status": "failure", "remarks": str(e), "data": ""}

    async def quote_data(self, securities):
        try:
            url = self.base_url + "/marketfeed/quote"
            payload = json_dumps({k: v for k, v in securities.items()})
            headers = {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "access-token": self.access_token,
                "client-id": self.client_id,
            }
            resp = await self.session.post(url, headers=headers, data=payload)
            return await self._parse_response(resp)
        except Exception as e:  # pragma: no cover - defensive
            logging.error("Exception in AsyncDhanhq>>quote_data: %s", e)
            return {"status": "failure", "remarks": str(e), "data": ""}
