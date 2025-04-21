import streamlit as st
import openai
import boto3
import json
import os
from io import BytesIO
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
openai.api_key = st.secrets["OPENAI_API_KEY"]

# SQS configuration
sqs = boto3.client("sqs", region_name="us-east-1")  # Replace with your AWS region
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/341336709396/AutoAssistantWithVoice-SQSTriggertoLambda"  # Replace with your actual SQS URL

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
                message = {"query": final_input}
                sqs.send_message(
                    QueueUrl=QUEUE_URL,
                    MessageBody=json.dumps(message)
                )
                st.success("✅ Your issue has been submitted to our diagnosis queue. You will be notified once processing is complete.")
            except Exception as e:
                st.error(f"Error sending to queue: {e}")
