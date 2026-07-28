from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.parse

# Path to datasets
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
CUSTOMERS_CSV = os.path.join(PROJECT_ROOT, 'src', 'processed_customers.csv')

customers_data = []
if os.path.exists(CUSTOMERS_CSV):
    try:
        import csv
        with open(CUSTOMERS_CSV, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            customers_data = [row for row in reader]
    except Exception as e:
        print(f"Error loading CSV in Vercel function: {e}")

# Default sample customers fallback if dataset file is omitted in deployment
if not customers_data:
    customers_data = [
        { 'Customer ID': '7590-VHVEG', 'Tenure in Months': '1', 'Contract': 'Month-to-month', 'Monthly Charge': '29.85', 'Internet Type': 'DSL', 'City': 'Los Angeles', 'Premium Tech Support': 'No' },
        { 'Customer ID': '5575-GNVDE', 'Tenure in Months': '34', 'Contract': 'One Year', 'Monthly Charge': '56.95', 'Internet Type': 'DSL', 'City': 'San Diego', 'Premium Tech Support': 'Yes' },
        { 'Customer ID': '3668-QVRHG', 'Tenure in Months': '2', 'Contract': 'Month-to-month', 'Monthly Charge': '53.85', 'Internet Type': 'DSL', 'City': 'San Jose', 'Premium Tech Support': 'No' },
        { 'Customer ID': '7795-CFOCW', 'Tenure in Months': '45', 'Contract': 'One Year', 'Monthly Charge': '42.30', 'Internet Type': 'DSL', 'City': 'San Francisco', 'Premium Tech Support': 'Yes' },
        { 'Customer ID': '9237-HQJSL', 'Tenure in Months': '2', 'Contract': 'Month-to-month', 'Monthly Charge': '70.70', 'Internet Type': 'Fiber Optic', 'City': 'Fresno', 'Premium Tech Support': 'No' }
    ]

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == '/api/stats' or path == '/api/stats/':
            self.send_json(self.get_stats())
        elif path == '/api/customers' or path == '/api/customers/':
            self.send_json(customers_data[:50])
        elif path.startswith('/api/customer/'):
            cid = path.split('/api/customer/')[-1].strip('/')
            cust = next((c for c in customers_data if c.get('Customer ID') == cid), None)
            if cust:
                cust_copy = dict(cust)
                cust_copy['risk_score'] = self.calculate_risk(cust_copy)
                self.send_json(cust_copy)
            else:
                self.send_json({'error': 'Customer not found'}, status=404)
        else:
            self.send_json({'status': 'ChurnGuard AI Vercel API Active', 'endpoints': ['/api/stats', '/api/customers', '/api/customer/<id>']})

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        if parsed_url.path == '/api/predict' or parsed_url.path == '/api/predict/':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                risk_score = self.calculate_risk(data)
                self.send_json({'risk_score': risk_score, 'status': 'success'})
            except Exception as e:
                self.send_json({'error': str(e)}, status=400)
        else:
            self.send_json({'error': 'Not found'}, status=404)

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def get_stats(self):
        total = len(customers_data)
        return {
            'totalCustomers': total,
            'churnRate': 26.5,
            'highRiskCount': int(total * 0.265),
            'revenueAtRisk': 142500,
            'contractDistribution': {'Month-to-Month': 55, 'One Year': 24, 'Two Year': 21},
            'tenureBreakdown': {
                'labels': ['0-6 Mo', '6-12 Mo', '12-24 Mo', '24-48 Mo', '48+ Mo'],
                'churned': [52, 38, 25, 14, 7],
                'stayed': [48, 62, 75, 86, 93]
            },
            'chargesBreakdown': {
                'labels': ['$20-40', '$40-60', '$60-80', '$80-100', '$100+'],
                'rates': [10, 16, 30, 48, 62]
            },
            'churnReasons': {
                'labels': [
                    'Competitor offered higher download speeds',
                    'Competitor offered more data',
                    'Attitude of support person',
                    'Price too high',
                    'Network reliability issues'
                ],
                'counts': [312, 280, 210, 195, 140]
            }
        }

    def calculate_risk(self, c):
        score = 0.25
        contract = str(c.get('Contract', 'Month-to-month'))
        if contract == 'Month-to-month': score += 0.35
        elif contract == 'One Year': score += 0.05
        elif contract == 'Two Year': score -= 0.15

        try:
            tenure = float(c.get('Tenure in Months', c.get('Tenure', 12)))
            if tenure < 6: score += 0.25
            elif tenure < 12: score += 0.15
            elif tenure > 36: score -= 0.20
        except:
            pass

        try:
            monthly = float(c.get('Monthly Charge', c.get('MonthlyCharge', 70)))
            if monthly > 85: score += 0.15
        except:
            pass

        return round(min(max(score, 0.05), 0.98), 2)
