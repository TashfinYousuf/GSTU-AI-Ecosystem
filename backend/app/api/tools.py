import os
import google as genai
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from fpdf import FPDF
from app.core.security import get_current_user

router = APIRouter()

class PDFRequest(BaseModel):
    title: str
    content: str

# 👁️ 1. Handwritten Note Analysis (Gemini Vision)
@router.post("/vision/analyze")
async def analyze_handwritten_note(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """হাতে লেখা নোট বা ডায়াগ্রাম আপলোড করলে AI সেটি পড়ে ডিজিটাল টেক্সটে কনভার্ট করবে"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not file.filename.endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Only Image files are supported.")

    try:
        # Save temp image
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Call Gemini Vision (1.5 Flash is natively multimodal)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Upload to Gemini File API
        sample_file = genai.upload_file(path=file_path, display_name="Handwritten Note")
        
        response = model.generate_content([
            sample_file, 
            "Analyze this handwritten academic note or diagram. Digitize the text accurately. If it contains a concept, explain it briefly in markdown format."
        ])

        # Cleanup
        os.remove(file_path)
        genai.delete_file(sample_file.name)

        return {"status": "success", "digitized_text": response.text}

    except Exception as e:
        print(f"Vision Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to process image.")


# 📄 2. Text-to-PDF Generator (Report Builder)
@router.post("/pdf/generate")
async def generate_pdf_report(request: PDFRequest, current_user: dict = Depends(get_current_user)):
    """AI এর রেসপন্স বা রিসার্চ নোট থেকে সুন্দর PDF তৈরি করে ডাউনলোডের জন্য দেবে"""
    if not current_user.get("sub"):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt=request.title, ln=True, align='C')
        pdf.ln(10)
        
        # Body (Using multi_cell for wrapping text)
        pdf.set_font("Arial", size=12)
        # Handle unicode encoding safely for basic FPDF
        safe_content = request.content.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 10, txt=safe_content)
        
        # Save PDF
        output_path = f"temp_exports/{current_user.get('sub')}_report.pdf"
        os.makedirs("temp_exports", exist_ok=True)
        pdf.output(output_path)
        
        # Return File directly
        return FileResponse(path=output_path, filename=f"{request.title}.pdf", media_type='application/pdf')

    except Exception as e:
        print(f"PDF Gen Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate PDF.")