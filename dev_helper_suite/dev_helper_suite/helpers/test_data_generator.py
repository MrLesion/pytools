"""Generate deterministic synthetic customers, products or linked orders."""
import random
from common import main, report


def generate(kind, count, seed):
    rng = random.Random(seed)
    def customer(i):
        return {'id': f'C{i:05}', 'name': f'Test Customer {i}', 'email': f'customer{i}@example.com',
                'address': {'street': f'Test Street {i}', 'postalCode': f'{rng.randint(1000, 9999)}', 'city': 'Test City', 'country': 'DK'}}
    def product(i):
        return {'id': f'P{i:05}', 'sku': f'SKU-{i:05}', 'name': f'Test Product {i}',
                'price': round(rng.uniform(10, 2000), 2), 'currency': 'DKK',
                'stock': rng.randint(0, 100), 'variants': [{'id': f'P{i:05}-{s}', 'size': s} for s in ('S', 'M', 'L')]}
    if kind == 'customers':
        return [customer(i) for i in range(1, count + 1)]
    if kind == 'products':
        return [product(i) for i in range(1, count + 1)]
    if kind != 'orders':
        raise ValueError('Kind must be products, customers or orders.')
    customers = [customer(i) for i in range(1, count + 1)]
    products = [product(i) for i in range(1, count + 1)]
    orders = []
    for i in range(1, count + 1):
        lines = []
        for prod in rng.sample(products, min(len(products), rng.randint(1, 4))):
            lines.append({'productId': prod['id'], 'quantity': rng.randint(1, 5), 'unitPrice': prod['price']})
        total = sum(round(x['unitPrice'] * 100) * x['quantity'] for x in lines) / 100
        orders.append({'id': f'O{i:05}', 'customerId': rng.choice(customers)['id'], 'currency': 'DKK',
                       'reference': f'TEST-{i:05}', 'lines': lines, 'total': total})
    return {'customers': customers, 'products': products, 'orders': orders}


def run(p):
    """Generate synthetic records; use Export result in the app to save them."""
    count = int(p.get('count', 10))
    if not 1 <= count <= 10000:
        raise ValueError('Count must be between 1 and 10000.')
    kind = p.get('kind', 'products')
    return report(f'Generated {count} {kind}; seed {p.get("seed", 42)}', data=generate(kind, count, int(p.get('seed', 42))))


if __name__ == '__main__':
    raise SystemExit(main(run))
