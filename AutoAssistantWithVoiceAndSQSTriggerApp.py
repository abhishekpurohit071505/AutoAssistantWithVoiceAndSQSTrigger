import streamlit as st
import openai
import boto3
import json
import os
import time
import uuid
from io import BytesIO
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
openai.api_key = st.secrets["OPENAI_API_KEY"]

# SQS configuration
sqs = boto3.client("sqs", region_name="us-east-1")  # Replace with your AWS region
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")

QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/341336709396/AutoAssistantWithVoice-SQSTriggertoLambda"  # Replace with your actual SQS URL
TABLE_NAME = "AutoFixDiagnoses"

st.set_page_config(page_title="AutoFix Assistant", layout="centered")
st.title("🔧 AutoFix Assistant")
st.subheader("Diagnose and Fix Your Vehicle Problems")

audio_file = st.file_uploader("Upload your voice (MP3, WAV, M4A)", type=["mp3", "wav", "m4a"])
user_input = st.text_area("Or type your issue below:", placeholder="e.g., My car is making noise while driving")

if st.button("🚀 Diagnose"):
    final_input = user_input.strip()

    if not final_input and audio_file:
        st.info("Transcribing your audio with Whisper...")
        try:
            audio_file.name = "audio.wav"
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            final_input = transcript.text
            st.success(f"Transcribed: {final_input}")
        except Exception as e:
            st.error(f"Transcription failed: {e}")
            final_input = ""

    if not final_input:
        st.warning("Please type or upload a description of your issue.")
    else:
        with st.spinner("Sending your request to our diagnosis queue..."):
            try:
                request_id = str(uuid.uuid4())
                message = {"query": final_input,"id": request_id }
                sqs.send_message(
                    QueueUrl=QUEUE_URL,
                    MessageBody=json.dumps(message)
                )
                st.success("✅ Your issue has been submitted to our diagnosis queue. You will be notified once processing is complete.")
                
                # Poll DynamoDB for the result
                table = dynamodb.Table(TABLE_NAME)
                result = None
                max_retries = 20
                for _ in range(max_retries):
                    response = table.get_item(Key={"id": request_id})
                    if "Item" in response:
                        result = response["Item"]
                        break
                    time.sleep(3)  # Wait before retrying

                if result:
                    st.markdown("### 🩺 Diagnosis Result:")
                    st.markdown(f"**🔍 Problem:** {result.get('input', 'N/A')}")
                    diagnosis = result.get("diagnosis", "")
                    if "Reason:" in diagnosis:
                        cause = diagnosis.split("Cause:", 1)[1].split("Reason:")[0].strip()
                        reason = diagnosis.split("Reason:", 1)[1].strip()
                    else:
                        cause, reason = diagnosis, ""
                    st.markdown(f"**💥 Cause:** {cause}")
                    st.markdown(f"**🧠 Reason:** {reason}")
                    st.markdown("---")
                    st.markdown(f"**🛠 Fix Guide:**\n\n{result.get('fix_guide', '')}", unsafe_allow_html=True)
                else:
                    st.warning("Diagnosis not yet available. Please try again later.")
                
                
                
                
            except Exception as e:
                st.error(f"Error sending to queue: {e}")
