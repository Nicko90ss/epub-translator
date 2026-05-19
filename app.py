import os
import uuid
import threading
from flask import Flask, request, send_file, render_template, jsonify
from werkzeug.utils import secure_filename
from epub import process_file_to_text

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
app.config['OUTPUT_FOLDER'] = '/tmp/outputs'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# Track job status
jobs = {}

ALLOWED_EXTENSIONS = {'epub', 'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def run_translation(job_id, input_path, output_path):
    try:
        jobs[job_id]['status'] = 'translating'
        text = process_file_to_text(input_path, job_id, jobs)
        if text:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            jobs[job_id]['status'] = 'done'
        else:
            jobs[job_id]['status'] = 'error'
            jobs[job_id]['error'] = 'No text could be extracted'
    except Exception as e:
        jobs[job_id]['status'] = 'error'
        jobs[job_id]['error'] = str(e)
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'error': 'Only .epub and .pdf files are supported'}), 400

    filename = secure_filename(file.filename)
    job_id = str(uuid.uuid4())[:8]
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{job_id}_{filename}")
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_translated.txt")

    file.save(input_path)
    jobs[job_id] = {'status': 'queued', 'progress': 0, 'total': 0, 'filename': filename}

    thread = threading.Thread(target=run_translation, args=(job_id, input_path, output_path))
    thread.daemon = True
    thread.start()

    return jsonify({'job_id': job_id})

@app.route('/status/<job_id>')
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)

@app.route('/download/<job_id>')
def download(job_id):
    job = jobs.get(job_id)
    if not job or job['status'] != 'done':
        return jsonify({'error': 'Not ready'}), 400
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{job_id}_translated.txt")
    original_name = os.path.splitext(job['filename'])[0]
    return send_file(output_path, as_attachment=True, download_name=f"{original_name}_translated.txt")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
