import os
import subprocess
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Create a Flask application
app = Flask(__name__)
# Set the configuration for our app
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

# Enable Cross-Origin Resource Sharing (CORS)
CORS(app)

# --- Helper Function ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- API Endpoints ---

@app.route('/api/upload', methods=['POST'])
def upload_and_process_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        
        # Create folders if they don't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        original_filepath = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
        file.save(original_filepath)

        command = [
            "fawkes",
            "-m", "high",
            "--directory", app.config['UPLOAD_FOLDER']
        ]

        try:
            # We run fawkes. It saves the output in the main project directory.
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print(f"Fawkes Error STDERR: {e.stderr}")
            return jsonify({"error": "An error occurred during image processing", "details": e.stderr}), 500

        base_name = original_filename.rsplit('.', 1)[0]
        processed_filename = f"{base_name}_cloaked.png"

        # The cloaked file is created in the root, so we check there
        processed_file_path_src = os.path.join(processed_filename)
        
        if not os.path.exists(app.config['PROCESSED_FOLDER']):
            os.makedirs(app.config['PROCESSED_FOLDER'])
            
        processed_file_path_dest = os.path.join(app.config['PROCESSED_FOLDER'], processed_filename)

        if os.path.exists(processed_file_path_src):
            os.rename(processed_file_path_src, processed_file_path_dest)
        else:
             return jsonify({"error": "Processing finished, but the output file was not found."}), 500

        # Create the full, public URL for the download link
        download_url = f"{request.host_url}api/get-image/{processed_filename}"
        
        return jsonify({
            "message": "File processed successfully!",
            "download_url": download_url
        })
    
    return jsonify({"error": "Invalid file type"}), 400


@app.route('/api/get-image/<filename>')
def get_image(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)


@app.route('/api/health')
def health_check():
    return jsonify({"status": "ok"}), 200