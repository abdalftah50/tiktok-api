from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import tempfile
import threading
import time
import uuid
import requests
from urllib.parse import urlparse
import json
import logging

# إعداد التطبيق
app = Flask(__name__)
CORS(app)  # للسماح بالطلبات من المواقع الأخرى
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB max

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# مجلد مؤقت للتحميلات
TEMP_FOLDER = tempfile.gettempdir()
download_sessions = {}

class TikTokAPI:
    def __init__(self):
        self.base_opts = {
            'format': 'best[height<=720]/best',
            'no_warnings': True,
            'quiet': True,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
        }
    
    def validate_url(self, url):
        """التحقق من صحة رابط TikTok"""
        tiktok_domains = ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com']
        try:
            parsed = urlparse(url)
            return any(domain in parsed.netloc for domain in tiktok_domains)
        except:
            return False
    
    def get_video_info(self, url):
        """استخراج معلومات الفيديو"""
        try:
            if not self.validate_url(url):
                return {'error': 'رابط TikTok غير صحيح'}
            
            opts = self.base_opts.copy()
            opts['skip_download'] = True
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    'success': True,
                    'data': {
                        'id': info.get('id', ''),
                        'title': info.get('title', 'بدون عنوان'),
                        'uploader': info.get('uploader', 'مجهول'),
                        'uploader_id': info.get('uploader_id', ''),
                        'duration': info.get('duration', 0),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'comment_count': info.get('comment_count', 0),
                        'repost_count': info.get('repost_count', 0),
                        'thumbnail': info.get('thumbnail', ''),
                        'description': info.get('description', ''),
                        'webpage_url': info.get('webpage_url', url),
                        'upload_date': info.get('upload_date', ''),
                        'formats': self.extract_formats(info.get('formats', []))
                    }
                }
        except Exception as e:
            logger.error(f"خطأ في استخراج معلومات الفيديو: {str(e)}")
            return {'error': f'فشل في استخراج المعلومات: {str(e)}'}
    
    def extract_formats(self, formats):
        """استخراج صيغ الفيديو المتاحة"""
        quality_formats = []
        for f in formats:
            if f.get('vcodec') != 'none':  # فيديو وليس صوت فقط
                quality_formats.append({
                    'format_id': f.get('format_id'),
                    'quality': f.get('height', 0),
                    'fps': f.get('fps', 0),
                    'filesize': f.get('filesize', 0),
                    'ext': f.get('ext', 'mp4')
                })
        
        # ترتيب حسب الجودة
        return sorted(quality_formats, key=lambda x: x['quality'], reverse=True)
    
    def download_video(self, url, session_id, quality='best', audio_only=False):
        """تحميل الفيديو"""
        try:
            if not self.validate_url(url):
                download_sessions[session_id] = {'status': 'error', 'error': 'رابط غير صحيح'}
                return
            
            download_sessions[session_id] = {
                'status': 'downloading',
                'progress': 0,
                'speed': 0,
                'eta': 0,
                'filename': '',
                'filepath': ''
            }
            
            # إعداد خيارات التحميل
            filename = f"{session_id}.%(ext)s"
            filepath = os.path.join(TEMP_FOLDER, filename)
            
            opts = self.base_opts.copy()
            opts['outtmpl'] = filepath
            
            if audio_only:
                opts['format'] = 'bestaudio/best'
                opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            elif quality != 'best':
                opts['format'] = f'best[height<={quality}]/best'
            
            def progress_hook(d):
                if d['status'] == 'downloading':
                    if d.get('total_bytes') or d.get('total_bytes_estimate'):
                        total = d.get('total_bytes') or d.get('total_bytes_estimate')
                        downloaded = d.get('downloaded_bytes', 0)
                        progress = (downloaded / total) * 100
                        
                        download_sessions[session_id].update({
                            'progress': round(progress, 2),
                            'speed': d.get('speed', 0),
                            'eta': d.get('eta', 0),
                            'downloaded_bytes': downloaded,
                            'total_bytes': total
                        })
                
                elif d['status'] == 'finished':
                    actual_filename = os.path.basename(d['filename'])
                    download_sessions[session_id].update({
                        'status': 'completed',
                        'progress': 100,
                        'filename': actual_filename,
                        'filepath': d['filename'],
                        'filesize': os.path.getsize(d['filename']) if os.path.exists(d['filename']) else 0
                    })
            
            opts['progress_hooks'] = [progress_hook]
            
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
                
        except Exception as e:
            logger.error(f"خطأ في التحميل: {str(e)}")
            download_sessions[session_id] = {
                'status': 'error',
                'error': str(e)
            }

# إنشاء كائن API
api = TikTokAPI()

# ================== API Endpoints ==================

@app.route('/', methods=['GET'])
def home():
    """معلومات API"""
    return jsonify({
        'name': 'TikTok Downloader API',
        'version': '1.0',
        'description': 'API لتحميل مقاطع TikTok',
        'endpoints': {
            'GET /': 'معلومات API',
            'POST /info': 'الحصول على معلومات الفيديو',
            'POST /download': 'بدء تحميل الفيديو',
            'GET /progress/<session_id>': 'تتبع تقدم التحميل',
            'GET /file/<session_id>': 'تحميل الملف',
            'DELETE /file/<session_id>': 'حذف الملف'
        },
        'status': 'online'
    })

@app.route('/info', methods=['POST'])
def get_video_info():
    """الحصول على معلومات الفيديو"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'يرجى إرسال رابط الفيديو'}), 400
        
        url = data['url'].strip()
        result = api.get_video_info(url)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"خطأ في /info: {str(e)}")
        return jsonify({'error': 'خطأ في الخادم'}), 500

@app.route('/download', methods=['POST'])
def start_download():
    """بدء تحميل الفيديو"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'يرجى إرسال رابط الفيديو'}), 400
        
        url = data['url'].strip()
        quality = data.get('quality', 'best')
        audio_only = data.get('audio_only', False)
        
        # إنشاء معرف جلسة فريد
        session_id = str(uuid.uuid4())
        
        # بدء التحميل في thread منفصل
        thread = threading.Thread(
            target=api.download_video,
            args=(url, session_id, quality, audio_only)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'بدأ التحميل'
        })
        
    except Exception as e:
        logger.error(f"خطأ في /download: {str(e)}")
        return jsonify({'error': 'خطأ في بدء التحميل'}), 500

@app.route('/progress/<session_id>', methods=['GET'])
def get_progress(session_id):
    """تتبع تقدم التحميل"""
    if session_id not in download_sessions:
        return jsonify({'error': 'معرف الجلسة غير موجود'}), 404
    
    session_data = download_sessions[session_id].copy()
    
    # تنسيق البيانات للعرض
    if 'speed' in session_data and session_data['speed']:
        session_data['speed_formatted'] = f"{session_data['speed']/1024/1024:.1f} MB/s"
    
    if 'total_bytes' in session_data and session_data['total_bytes']:
        total_mb = session_data['total_bytes'] / 1024 / 1024
        session_data['total_size_formatted'] = f"{total_mb:.1f} MB"
    
    return jsonify(session_data)

@app.route('/file/<session_id>', methods=['GET'])
def download_file(session_id):
    """تحميل الملف"""
    if session_id not in download_sessions:
        return jsonify({'error': 'معرف الجلسة غير موجود'}), 404
    
    session = download_sessions[session_id]
    
    if session.get('status') != 'completed':
        return jsonify({'error': 'التحميل غير مكتمل'}), 400
    
    filepath = session.get('filepath')
    if not filepath or not os.path.exists(filepath):
        return jsonify({'error': 'الملف غير موجود'}), 404
    
    return send_file(
        filepath,
        as_attachment=True,
        download_name=session.get('filename', 'video.mp4')
    )

@app.route('/file/<session_id>', methods=['DELETE'])
def delete_file(session_id):
    """حذف الملف"""
    if session_id in download_sessions:
        session = download_sessions[session_id]
        filepath = session.get('filepath')
        
        if filepath and os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass
        
        del download_sessions[session_id]
        return jsonify({'success': True, 'message': 'تم حذف الملف'})
    
    return jsonify({'error': 'معرف الجلسة غير موجود'}), 404

@app.route('/sessions', methods=['GET'])
def list_sessions():
    """عرض جلسات التحميل النشطة"""
    return jsonify({
        'active_sessions': len(download_sessions),
        'sessions': {k: {
            'status': v.get('status'),
            'progress': v.get('progress', 0)
        } for k, v in download_sessions.items()}
    })

@app.route('/cleanup', methods=['POST'])
def cleanup_old_files():
    """تنظيف الملفات القديمة"""
    try:
        cleaned = 0
        current_time = time.time()
        
        # حذف الجلسات المكتملة القديمة (أكثر من ساعة)
        to_delete = []
        for session_id, session in download_sessions.items():
            if session.get('status') == 'completed':
                filepath = session.get('filepath')
                if filepath and os.path.exists(filepath):
                    file_age = current_time - os.path.getctime(filepath)
                    if file_age > 3600:  # ساعة واحدة
                        os.remove(filepath)
                        to_delete.append(session_id)
                        cleaned += 1
        
        for session_id in to_delete:
            del download_sessions[session_id]
        
        return jsonify({
            'success': True,
            'cleaned_files': cleaned,
            'message': f'تم تنظيف {cleaned} ملف'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# معالج الأخطاء
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'الصفحة غير موجودة'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'خطأ في الخادم'}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'حجم الطلب كبير جداً'}), 413

if __name__ == '__main__':
    print("🚀 بدء تشغيل TikTok API...")
    print("📍 العنوان: http://localhost:5000")
    print("📚 التوثيق: http://localhost:5000")
    print("🔧 البيئة: Development")
    print("="*50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)