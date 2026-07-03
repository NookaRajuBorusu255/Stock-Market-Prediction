from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from services.chatbot_service import get_chatbot_response
from database.database_helper import save_chat_message, get_user_chat_history, clear_user_chat_history

chatbot_bp = Blueprint('chatbot', __name__)

@chatbot_bp.route('/chatbot')
@login_required
def chat_view():
    """
    Renders the chatbot portal page.
    """
    return render_template('chatbot.html')

@chatbot_bp.route('/api/chatbot/message', methods=['POST'])
@login_required
def post_message():
    """
    Handles user prompts, saves conversation log, and returns AI Assistant responses.
    """
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        active_symbol = data.get('active_symbol')
        active_model = data.get('active_model')
        
        if not message:
            return jsonify({'error': 'Message is empty'}), 400
            
        # Save user message to SQL
        save_chat_message(current_user.id, 'user', message)
        
        # Get AI response
        ai_response = get_chatbot_response(message, active_symbol, active_model)
        
        # Save bot response to SQL
        save_chat_message(current_user.id, 'bot', ai_response)
        
        return jsonify({'success': True, 'response': ai_response})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@chatbot_bp.route('/api/chatbot/history', methods=['GET'])
@login_required
def get_history():
    """
    Fetches the logged-in user's chat message history log.
    """
    try:
        messages = get_user_chat_history(current_user.id)
        history = [{'sender': m.sender, 'message': m.message} for m in messages]
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@chatbot_bp.route('/api/chatbot/clear', methods=['POST'])
@login_required
def clear_history():
    """
    Deletes the logged-in user's chat history log.
    """
    try:
        clear_user_chat_history(current_user.id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400
