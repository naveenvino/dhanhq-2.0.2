import argparse
import json
from .dhanhq import dhanhq


def parse_args():
    parser = argparse.ArgumentParser(description="CLI for DhanHQ API")
    parser.add_argument("client_id", help="Dhan client id")
    parser.add_argument("access_token", help="Dhan access token")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-orders", help="List today's orders")

    get_order = subparsers.add_parser("get-order", help="Get order by id")
    get_order.add_argument("order_id")

    place = subparsers.add_parser("place-order", help="Place a simple order")
    place.add_argument("security_id")
    place.add_argument("exchange_segment")
    place.add_argument("transaction_type")
    place.add_argument("quantity", type=int)
    place.add_argument("order_type")
    place.add_argument("product_type")
    place.add_argument("price", type=float)

    subparsers.add_parser("positions", help="Get open positions")

    return parser.parse_args()


def main():
    args = parse_args()
    api = dhanhq(args.client_id, args.access_token)

    if args.command == "list-orders":
        resp = api.get_order_list()
    elif args.command == "get-order":
        resp = api.get_order_by_id(args.order_id)
    elif args.command == "place-order":
        resp = api.place_order(
            security_id=args.security_id,
            exchange_segment=args.exchange_segment,
            transaction_type=args.transaction_type,
            quantity=args.quantity,
            order_type=args.order_type,
            product_type=args.product_type,
            price=args.price,
        )
    elif args.command == "positions":
        resp = api.get_positions()
    else:
        return

    print(json.dumps(resp, indent=2))


if __name__ == "__main__":
    main()
