import http.server
import socketserver
import json
import os
import urllib.parse
import pandas as pd
import numpy as np

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# Try loading dataset for API responses
CUSTOMERS_CSV = os.path.join(DIRECTORY, 'src', 'processed_customers.csv')
if not os.path.exists(CUSTOMERS_CSV):
    CUSTOMERS_CSV = os.path.join(DIRECTORY, 'processed_customers.csv')

df_customers = pd.DataFrame()
if os.path.exists(CUSTOMERS_CSV):
    try:
        df_customers = pd.read_csv(CUSTOMERS_CSV)
        print(f"[Server] Loaded {len(df_customers)} customers from {CUSTOMERS_CSV}")
    except Exception as e:
        print(f"[Server] Error reading dataset CSV: {e}")

class ChurnAppHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == '/api/stats':
            self.send_json(self.get_stats())
        elif path == '/api/customers':
            self.send_json(self.get_customers())
        elif path.startswith('/api/customer/'):
            customer_id = path.split('/api/customer/')[-1]
            self.send_json(self.get_customer_detail(customer_id))
        else:
            super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == '/api/predict':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                risk_score = self.calculate_risk(data)
                self.send_json({'risk_score': risk_score, 'status': 'success'})
            except Exception as e:
                self.send_json({'error': str(e)}, status=400)
        else:
            self.send_error(404, "Endpoint not found")

    def send_json(self, data, status=200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def get_stats(self):
        total = len(df_customers) if not df_customers.empty else 7043
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

    def get_customers(self):
        if not df_customers.empty:
            sample = df_customers.head(50).fillna('')
            return sample.to_dict(orient='records')
        return []

    def get_customer_detail(self, cid):
        if not df_customers.empty and 'Customer ID' in df_customers.columns:
            match = df_customers[df_customers['Customer ID'] == cid]
            if not match.empty:
                cust = match.iloc[0].fillna('').to_dict()
                cust['risk_score'] = self.calculate_risk(cust)
                return cust
        return {'error': 'Customer not found'}

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

if __name__ == "__main__":
    print("==================================================")
    print("Starting ChurnGuard AI Web Application Server")
    print(f"Server URL: http://localhost:{PORT}")
    print("==================================================")
    with socketserver.TCPServer(("", PORT), ChurnAppHandler) as httpd:
        httpd.serve_forever()
