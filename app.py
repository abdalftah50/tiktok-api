from flask import Flask, request, jsonify
from downloader import get_download_url

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ TikTok API جاهز للعمل!"

@app.route('/api/tiktok', methods=['POST'])
def tiktok_download():
    video_url = request.form.get('url')
    if not video_url:
        return jsonify({'status': 'error', 'message': 'يرجى إدخال رابط TikTok'}), 400
    
    result = get_download_url(video_url)
    return jsonify(result)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
