
import os
import sys
from app import app

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    app.run(debug=True, host='0.0.0.0', port=port)
