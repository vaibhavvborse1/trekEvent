import streamlit as st
import json
import os
from copy import deepcopy
import os
import uuid
import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO


# helpers_marketing.py (paste into your app.py)
import os
import uuid
import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO

def make_trek_id(name: str) -> str:
    short = "".join(ch for ch in name.lower() if ch.isalnum())[:12]
    return f"{short}-{uuid.uuid4().hex[:6]}"

def ensure_dirs(base="trek_assets"):
    os.makedirs(base, exist_ok=True)
    return base

def generate_qr(data: str, out_path: str):
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=6, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(out_path)
    return out_path

def create_social_banner(trek: dict, main_image_path: str, out_path: str, width=1200, height=630):
    """
    Simple social banner: main image as background (center-cropped), text overlay with trek name/date.
    """
    # open image and resize/center-crop
    bg = Image.open(main_image_path).convert("RGBA")
    # center crop to target aspect
    src_w, src_h = bg.size
    target_ratio = width / height
    src_ratio = src_w / src_h
    if src_ratio > target_ratio:
        # crop width
        new_w = int(target_ratio * src_h)
        left = (src_w - new_w) // 2
        bg = bg.crop((left, 0, left + new_w, src_h))
    else:
        # crop height
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        bg = bg.crop((0, top, src_w, top + new_h))
    bg = bg.resize((width, height), Image.LANCZOS)

    # overlay gradient for text contrast
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 80))
    combined = Image.alpha_composite(bg, overlay)

    draw = ImageDraw.Draw(combined)
    # choose a font. On many systems DejaVuSans is available; fallback if not.
    try:
        font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
        font_sub = ImageFont.truetype("DejaVuSans.ttf", 28)
    except Exception:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # write text: name (wrapped) and date
    title = trek.get("name", "Untitled Trek")
    date = trek.get("date", "")
    # position text bottom-left
    padding = 32
    draw.text((padding, height - 140), title, font=font_title, fill=(255,255,255,255))
    draw.text((padding, height - 80), date, font=font_sub, fill=(255,255,255,220))

    # save as PNG
    combined.convert("RGB").save(out_path, format="PNG", quality=90)
    return out_path

def create_flyer_pdf(trek: dict, main_image_path: str, qr_path: str, out_pdf_path: str):
    """
    Create a simple A4 PDF with main image on top, details below and QR code at corner.
    """
    c = canvas.Canvas(out_pdf_path, pagesize=A4)
    W, H = A4

    # place image at top (fit width)
    try:
        img = Image.open(main_image_path)
        # fit image width to page minus margins
        max_w = W - 80
        w_ratio = max_w / img.width
        new_w = max_w
        new_h = img.height * w_ratio
        # save a temp resized image to bytes
        img_resized = img.resize((int(new_w), int(new_h)))
        buf = BytesIO()
        img_resized.save(buf, format="JPEG")
        buf.seek(0)
        c.drawImage(buf, 40, H - 40 - new_h, width=new_w, height=new_h)
    except Exception:
        # ignore if image fails, continue
        pass

    # details text below image
    y = H - 60 - new_h if 'new_h' in locals() else H - 120
    text_x = 40
    y -= 40
    c.setFont("Helvetica-Bold", 18)
    c.drawString(text_x, y, trek.get("name", "Untitled Trek"))
    y -= 26
    c.setFont("Helvetica", 12)
    c.drawString(text_x, y, f"Date: {trek.get('date','')}")
    y -= 18
    c.drawString(text_x, y, f"Location: {trek.get('location','')}")
    y -= 18
    c.drawString(text_x, y, f"Price: {trek.get('price','')}")
    y -= 22

    # draw a short intro paragraph (wrap lines)
    intro = trek.get("intro", "")
    from textwrap import wrap
    lines = wrap(intro, 90)
    for line in lines[:6]:
        y -= 16
        c.drawString(text_x, y, line)

    # draw QR at bottom-right
    try:
        qr_img = Image.open(qr_path)
        qr_w = 120
        qr_h = 120
        qr_buf = BytesIO()
        qr_img.resize((qr_w, qr_h)).save(qr_buf, format="PNG")
        qr_buf.seek(0)
        c.drawImage(qr_buf, W - 40 - qr_w, 40, width=qr_w, height=qr_h)
        c.setFont("Helvetica", 9)
        c.drawString(W - 40 - qr_w, 40 + qr_h + 6, "Scan for details / registration")
    except Exception:
        pass

    c.showPage()
    c.save()
    return out_pdf_path

def generate_caption_and_hashtags(trek: dict):
    """
    Simple caption template generator for social posts.
    """
    name = trek.get("name","Untitled Trek")
    date = trek.get("date","")
    location = trek.get("location","")
    price = trek.get("price","")
    caption = (f"🌄 {name} — {date}\n"
               f"📍 {location}\n"
               f"💰 {price}\n\n"
               "Join us for an unforgettable adventure! Limited spots — DM to book. 🥾\n\n"
               "#trekking #hiking #maharashtra #adventure #weekendgetaway")
    return caption

def generate_marketing_pack(trek: dict, main_image_path: str, base_dir="trek_assets"):
    """
    Orchestrator: returns dict with file paths for assets.
    """
    ensure_dirs(base_dir)
    trek_id = trek.get("id") or make_trek_id(trek.get("name","trek"))
    trek_dir = os.path.join(base_dir, trek_id)
    os.makedirs(trek_dir, exist_ok=True)

    # QR target: you can change this to your public trek page URL when deployed
    qr_data = f"TREK:{trek_id}|NAME:{trek.get('name','')}"
    qr_path = os.path.join(trek_dir, "qr.png")
    generate_qr(qr_data, qr_path)

    # Social banner
    social_path = os.path.join(trek_dir, "social.png")
    create_social_banner(trek, main_image_path, social_path)

    # PDF flyer
    pdf_path = os.path.join(trek_dir, "flyer.pdf")
    create_flyer_pdf(trek, main_image_path, qr_path, pdf_path)

    caption = generate_caption_and_hashtags(trek)

    return {
        "trek_id": trek_id,
        "dir": trek_dir,
        "qr": qr_path,
        "social": social_path,
        "pdf": pdf_path,
        "caption": caption
    }

# --------------------------------------------
# CONFIGURATION
# --------------------------------------------
st.set_page_config(page_title="Vedh girishikhranche", page_icon="", layout="wide")

EVENTS_FILE = "events.json"

# -----------------------------
# Default events (sample)
# -----------------------------
DEFAULT_EVENTS = [
    {
        "name": "Duke's Nose To Umberkhind | Historical Range Trek",
        "image": "https://imgs.search.brave.com/xeukn47z8WKDUlRjIwcr7C97BkyPwIA6pgfgsw4FVWo/rs:fit:860:0:0:0/g:ce/aHR0cHM6Ly92bC1w/cm9kLXN0YXRpYy5i/LWNkbi5uZXQvc3lz/dGVtL2ltYWdlcy8w/MDAvMzQ0LzEzMi80/NzY5NmYwNmNjYmRl/MmZmYzViYjE2ZDNl/OThhNTQwZi9vcmln/aW5hbC9JTUctMjAx/NTA5MTQtV0EwMDIw/LmpwZw",
        "location": "Sahyadri mountain ranges near Lonavala, Maharashtra, India.",
        "date": "26th Oct 2025, Sunday (Leaving Saturday Night – 25th Oct)",
        "difficulty": "Medium",
        "organiser": "Somesh H. Mahajan",
        "phone": "7558783213",
        "price": "₹1,199.00/- For each person",
        "intro": "Hi adventure lovers, Offbeat Special Historical Range Trek To “DUKE’S NOSE TO UMBERKHIND 🚩",
        "about_trek": "• *Duke’s Nose (Nagphani)*: A striking 1000 ft high pinnacle near Lonavala, shaped like a snake’s hood. A thrilling ascent with panoramic views!\n• *Umberkhind:* Historic battleground where Chhatrapati Shivaji Maharaj outwitted a larger Mughal force. A perfect blend of nature and Maratha history. Explore lush green trails and the Samarbhoomi Memorial.",
        "key_highlights": [
            "Range Trek covering 9-10 km",
            "Jungle trails, paddy fields, streams & river crossing",
            "Full descend trek",
            "Local village food",
            "Duke’s Nose Pinnacle",
            "War Memorial at Umberkhind"
        ],
        "detailed_schedule": "**Itinerary**\n- 1:50 AM – Travel to Base Village by Private Vehicle  \n- 2:30 AM – Reach Base & Rest  \n- 4:30 AM – Freshen up, Breakfast  \n- 5:30 AM – Start Trek  \n- 7:00 AM – Reach Top, Explore, Photos  \n- 8:00 AM – Descend to Umberkhind  \n- 11:00 AM – Reach War Memorial  \n- 12:00 PM – Lunch  \n- 3:00 PM – Depart\n",
        "inclusions": [
            "Breakfast (Poha + Tea)",
            "Local Lunch",
            "Local Transport (Lonavala to Kurvande & Umberkhind to Khopoli)",
            "Safety Equipment Charges",
            "Local Guide",
            "VGS Adventure Expertise"
        ],
        "exclusions": [
            "Train tickets",
            "Personal expenses",
            "Insurance/Medical coverage"
        ],
        "images": []
    },
    {
        "name": "Pabargad : One Day Offbeat Trek",
        "image": "https://imgs.search.brave.com/57rdeBVoLp6K7aJq-UsysZIlGl7MRyBuqUG_GnSyErY/rs:fit:500:0:1:0/g:ce/aHR0cHM6Ly9yZXMu/Y2xvdWRpbmFyeS5j/b20vZHd6bXN2cDdm/L2ltYWdlL2ZldGNo/L3FfNzUsZl9hdXRv/LHdfMTMxNi9odHRw/czovL21lZGlhLmlu/c2lkZXIuaW4vL2lt/YWdlL3VwbG9hZC9j/X2Nyb3AsZ19jdXN0/b20vdjE1NTIzMTE3/NzcvaWlkM3lncnZm/eXkwbWtoYml2aGQu/anBn",
        "location": "Guhire Village, Ahmednagar District, Maharashtra",
        "date": "12th October 2025 (Sunday)",
        "difficulty": "Medium",
        "organiser": "VGS Adventure India",
        "phone": "9356995738",
        "price": "₹1,399.00 per person",
        "intro": "Crowd-Free 'PabarGad Fort Offbeat Trek' — one-day, one-night journey into unexplored beauty and history.",
        "about_trek": "Nestled in the rustic landscapes of Ahmednagar district, *PabarGad* offers an offbeat trekking experience...",
        "key_highlights": [
            "Crowd-Free Trek",
            "Wild Flowers and Unexplored Beauty",
            "Ancient Water Tanks",
            "Temples of Bhairavnath, Ganesh & Hanuman"
        ],
        "detailed_schedule": "📅 **11th October 2025** (Saturday Night)\n- 10:47 pm: Board CST-Kasara Local Train\n\n📅 **12th October 2025** (Sunday)\n- 01:20 am: Meet at Kasara Railway Station Ticket Counter\n- 04:00 am: Reach base village & rest\n- 06:00 am: Begin trek\n- 12:30 pm: Return to base village and enjoy lunch\n",
        "inclusions": [
            "1 Breakfast and Tea",
            "1 Local Veg Lunch",
            "Transport (Kasara ↔ Base Village)",
            "Safety Equipment & First-Aid",
            "Local Guide",
            "Certified Leaders from VGS Adventure India"
        ],
        "exclusions": [
            "Personal expenses",
            "Anything not mentioned in inclusions",
            "Medical or emergency evacuations"
        ],
        "images": []
    }
]

# -----------------------------
# Credentials (previously missing)
# -----------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"
USER_USERNAME = "user1"
USER_PASSWORD = "user123"

# --------------------------------------------
# EVENTS: load / save
# --------------------------------------------
def load_events():
    """Load events from JSON file, or create file from defaults."""
    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception:
            # fallback to defaults
            return deepcopy(DEFAULT_EVENTS)
    else:
        # write defaults to file for persistence
        try:
            with open(EVENTS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_EVENTS, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        return deepcopy(DEFAULT_EVENTS)


def save_events(events):
    """Save events to JSON file."""
    try:
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error("Failed to save events: " + str(e))


# ---------------- Authentication ----------------
def do_login(username, password):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        st.session_state.logged_in = True
        st.session_state.role = "admin"
        st.session_state.username = username
        st.success("Admin login successful!")
        st.rerun()

    elif username == USER_USERNAME and password == USER_PASSWORD:
        st.session_state.logged_in = True
        st.session_state.role = "user"
        st.session_state.username = username
        st.success("User login successful!")
        st.rerun()

    else:
        st.error("Invalid username or password")


def do_logout():
    for k in ["logged_in", "username", "role", "edit_index", "pending_delete"]:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()


# ---------------- Trek Display ----------------
def show_trek_cards(events):
    cols = st.columns(2)
    for idx, trek in enumerate(events):
        with cols[idx % 2]:
            image_url = trek.get("image", "")
            if image_url:
                try:
                    st.image(image_url, use_container_width=True)
                except Exception:
                    # ignore image loading errors
                    pass
            st.subheader(trek.get("name", "Untitled"))
            st.write(f"📍 {trek.get('location','')}")
            st.write(f"📅 {trek.get('date','')}")
            st.write(f"💪 Difficulty: {trek.get('difficulty','')}")
            st.write(f"💰 {trek.get('price','')}")
            with st.expander("🔎 View Full Details"):
                st.markdown(f"### 🧭 About the Trek\n{trek.get('about_trek','')}")
                st.markdown("### 🌟 Highlights")
                for h in trek.get("key_highlights", []):
                    st.markdown(f"- {h}")
                st.markdown("### 🕒 Detailed Schedule")
                st.markdown(trek.get("detailed_schedule",""), unsafe_allow_html=True)
                st.markdown("### ✅ Inclusions")
                for inc in trek.get("inclusions", []):
                    st.markdown(f"- {inc}")
                st.markdown("### ❌ Exclusions")
                for exc in trek.get("exclusions", []):
                    st.markdown(f"- {exc}")
                st.markdown("### 🖼️ Gallery")
                gcols = st.columns(2)
                for i, img in enumerate(trek.get("images", [])):
                    with gcols[i % 2]:
                        try:
                            st.image(img, use_container_width=True)
                        except Exception:
                            pass

            phone = trek.get("phone", "")
            whatsapp_url = f"https://wa.me/{phone}?text=Hello!%20I'm%20interested%20in%20the%20{trek.get('name','')}." if phone else "#"
            st.markdown(
                f'<a href="{whatsapp_url}" target="_blank"><button style="padding:8px 20px;font-size:15px;background-color:#25D366;color:white;border:none;border-radius:6px;">💬 Chat with Expert</button></a>',
                unsafe_allow_html=True
            )
            st.divider()




# ---------------- Sidebar: User ----------------
def user_sidebar():
    st.sidebar.image(
        "https://1.bp.blogspot.com/-dJk9inaumCI/YU3jp80S_BI/AAAAAAAAWyg/sXoQmvLwoBo9NqxYbIoorcSpNBUjb9P3gCLcBGAsYHQ/s1440/vedhgirishikhranche.jpg",
        width=180
    )
    st.sidebar.markdown("## 🏔️ Vedh Girishikhranche")
    st.sidebar.markdown("**Adventure Awaits! Explore thrilling treks!**")
    st.sidebar.markdown("---")
    choice = st.sidebar.radio(
        "🌄 Choose Your Section:",
        ["🚩 Maharashtra Treks", "🌍 Outside Maharashtra", "📷 Gallery", "📞 Contact"]
    )
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔗 Follow Us On")
    st.sidebar.markdown(
    """
    <style>
    .social-icons {
        display: flex;
        gap: 18px;
        align-items: center;
        justify-content: flex-start;
        margin-top: 5px;
    }
    .social-icons img {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        transition: all 0.3s ease;
        box-shadow: 0 0 5px rgba(255,255,255,0.3);
    }
    .social-icons img:hover {
        transform: scale(1.2);
        box-shadow: 0 0 12px rgba(255, 100, 180, 0.8);
    }
    </style>
    <div class="social-icons">
    <a href="https://www.instagram.com/vedh_girishikharanche/" target="_blank" style="text-decoration:none;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/e/e7/Instagram_logo_2016.svg" width="25" style="vertical-align:middle; margin-right:8px;">
        <span style="font-size:16px; color:white; vertical-align:middle;">Instagram</span>
    </a>
    </div>
    """,
    unsafe_allow_html=True
)
    st.sidebar.markdown("[Facebook](https://facebook.com)")
    if st.sidebar.button("Logout"):
        do_logout()
    return choice

# ---------------- Sidebar: Admin ----------------
def admin_sidebar():
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👑 **Admin:** {st.session_state.get('username','')}")
    choice = st.sidebar.radio("Admin Menu", ["Dashboard", "Add Trek", "Manage Treks"])
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout"):
        do_logout()
    return choice


# ---------------- Admin Pages ----------------
def admin_dashboard(events):
    st.header("🔐 Admin Dashboard")
    st.write("Quick stats and preview")
    st.metric("Total Treks", len(events))
    next_dates = [e.get("date","") for e in events][:3]
    st.write("Upcoming (sample):")
    for d in next_dates:
        st.write("- " + d)
    st.markdown("---")
    st.subheader("Preview Site (first 4 treks)")
    show_trek_cards(events[:4])



def add_trek_page(events):
    st.header("➕ Add New Trek")

    with st.form("add_trek_form", clear_on_submit=True):
        name = st.text_input("🏔 Trek Name")

        # 🖼 Main Image Upload (works on mobile gallery/camera)
        main_image = st.file_uploader("🖼 Upload Main Image", type=["jpg", "jpeg", "png"])

        # 🖼 Multiple Gallery Image Uploads
        gallery_images = st.file_uploader(
            "📸 Upload Gallery Images (multiple allowed)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True
        )

        location = st.text_input("📍 Location")
        date = st.text_input("📅 Date")
        difficulty = st.selectbox("⚡ Difficulty", ["Easy", "Medium", "Hard"])
        organiser = st.text_input("👥 Organiser")
        phone = st.text_input("📞 Phone (digits only)")
        price = st.text_input("💰 Price / Cost")
        intro = st.text_area("📝 Intro (short)")
        about_trek = st.text_area("📖 About Trek (long)")
        detailed_schedule = st.text_area("🗓️ Detailed Schedule (markdown allowed)")
        key_highlights = st.text_area("⭐ Key Highlights (one per line)")
        inclusions = st.text_area("✅ Inclusions (one per line)")
        exclusions = st.text_area("❌ Exclusions (one per line)")
        
        submitted = st.form_submit_button("Add Trek")

        if submitted:
            if not name or not location or not date:
                st.warning("⚠️ Please fill in all required fields: Name, Location, Date.")
                return

            # 📂 Ensure folders exist
            os.makedirs("trek_images/main", exist_ok=True)
            os.makedirs("trek_images/gallery", exist_ok=True)

            # Save main image
            main_image_path = None
            if main_image:
                main_image_path = os.path.join("trek_images/main", main_image.name)
                with open(main_image_path, "wb") as f:
                    f.write(main_image.getbuffer())

            # Save gallery images
            gallery_paths = []
            if gallery_images:
                for img in gallery_images:
                    img_path = os.path.join("trek_images/gallery", img.name)
                    with open(img_path, "wb") as f:
                        f.write(img.getbuffer())
                    gallery_paths.append(img_path)

            # Create trek data dictionary
            new_trek = {
                "name": name,
                "image": main_image_path,          # local main image
                "location": location,
                "date": date,
                "difficulty": difficulty,
                "organiser": organiser,
                "phone": phone,
                "price": price,
                "intro": intro,
                "about_trek": about_trek,
                "detailed_schedule": detailed_schedule,
                "key_highlights": key_highlights.splitlines(),
                "inclusions": inclusions.splitlines(),
                "exclusions": exclusions.splitlines(),
                "gallery": gallery_paths         # list of local gallery images
            }

            # Add to event list (or database)
            events.append(new_trek)
            st.success(f"✅ Trek '{name}' added successfully!")

            # inside your add_trek_page after events.append(new_trek) and save_events(...)
            new_trek['id'] = make_trek_id(new_trek['name'])   # ensure ID saved
            assets = generate_marketing_pack(new_trek, main_image_path)
            
            st.success(f"✅ Trek '{name}' added successfully! Trek ID: {assets['trek_id']}")
            
            # Preview/Downloads
            st.subheader("Marketing Pack")
            st.image(assets['social'], caption="Auto social banner (download below)")
            
            with open(assets['pdf'], "rb") as f:
                pdf_bytes = f.read()
            st.download_button("⬇️ Download Flyer (PDF)", data=pdf_bytes, file_name=f"{assets['trek_id']}_flyer.pdf", mime="application/pdf")
            
            with open(assets['social'], "rb") as f:
                img_bytes = f.read()
            st.download_button("⬇️ Download Social Banner", data=img_bytes, file_name=f"{assets['trek_id']}_banner.png", mime="image/png")
            
            with open(assets['qr'], "rb") as f:
                qr_bytes = f.read()
            st.download_button("⬇️ Download QR", data=qr_bytes, file_name=f"{assets['trek_id']}_qr.png", mime="image/png")
            
            st.text_area("Suggested Caption (copy & paste to social)", value=assets['caption'], height=140)


            # Show previews
            if main_image_path:
                st.image(main_image_path, caption="Main Trek Image", use_container_width=True)

            if gallery_paths:
                st.subheader("📸 Gallery Preview")
                st.image(gallery_paths, width=200)
        if submitted:
            new = {
                "name": name,
                "image": image,
                "location": location,
                "date": date,
                "difficulty": difficulty,
                "organiser": organiser,
                "phone": phone,
                "price": price,
                "intro": intro,
                "about_trek": about_trek,
                "detailed_schedule": detailed_schedule,
                "key_highlights": [s.strip() for s in key_highlights.splitlines() if s.strip()],
                "inclusions": [s.strip() for s in inclusions.splitlines() if s.strip()],
                "exclusions": [s.strip() for s in exclusions.splitlines() if s.strip()],
                "images": [s.strip() for s in gallery.splitlines() if s.strip()]
            }
            events.append(new)
            save_events(events)
            st.success("Trek added successfully")
            st.rerun()


def manage_treks_page(events):
    st.header("📋 Manage Treks")
    st.write("Edit or delete existing treks")
    for idx, trek in enumerate(events):
        with st.expander(f"{idx+1}. {trek.get('name','Untitled')}"):
            st.write(f"📍 {trek.get('location','')}")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**Date:** {trek.get('date','')}")
                st.markdown(f"**Price:** {trek.get('price','')}")
                st.markdown("**Intro:**")
                st.write(trek.get("intro",""))
            with col2:
                if st.button(f"Edit {idx}", key=f"edit_{idx}"):
                    st.session_state["edit_index"] = idx
                    st.rerun()
                if st.button(f"Delete {idx}", key=f"delete_{idx}"):
                    st.session_state["pending_delete"] = idx
                    st.rerun()

    # Confirm deletion area
    if "pending_delete" in st.session_state:
        idx = st.session_state["pending_delete"]
        if 0 <= idx < len(events):
            st.warning(f"Are you sure you want to delete '{events[idx].get('name','')}'?")
            colc, cold = st.columns([1,1])
            with colc:
                if st.button("Confirm Delete"):
                    events.pop(idx)
                    save_events(events)
                    st.success("Deleted.")
                    del st.session_state["pending_delete"]
                    st.rerun()
            with cold:
                if st.button("Cancel"):
                    del st.session_state["pending_delete"]
                    st.rerun()

    # Editing form (if an index is set)
    if "edit_index" in st.session_state:
        i = st.session_state["edit_index"]
        if 0 <= i < len(events):
            st.markdown("---")
            st.subheader(f"Edit Trek: {events[i].get('name','')}")
            trek = events[i]
            with st.form("edit_trek_form"):
                name = st.text_input("Trek Name", value=trek.get("name",""))
                image = st.text_input("Main Image URL", value=trek.get("image",""))
                location = st.text_input("Location", value=trek.get("location",""))
                date = st.text_input("Date", value=trek.get("date",""))
                difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=["Easy","Medium","Hard"].index(trek.get("difficulty","Medium")) if trek.get("difficulty","Medium") in ["Easy","Medium","Hard"] else 1)
                organiser = st.text_input("Organiser", value=trek.get("organiser",""))
                phone = st.text_input("Phone (digits only)", value=trek.get("phone",""))
                price = st.text_input("Price / Cost", value=trek.get("price",""))
                intro = st.text_area("Intro (short)", value=trek.get("intro",""))
                about_trek = st.text_area("About Trek (long)", value=trek.get("about_trek",""))
                detailed_schedule = st.text_area("Detailed Schedule (markdown allowed)", value=trek.get("detailed_schedule",""))
                key_highlights = st.text_area("Key Highlights (one per line)", value="\n".join(trek.get("key_highlights", [])))
                inclusions = st.text_area("Inclusions (one per line)", value="\n".join(trek.get("inclusions", [])))
                exclusions = st.text_area("Exclusions (one per line)", value="\n".join(trek.get("exclusions", [])))
                gallery = st.text_area("Gallery image URLs (one per line)", value="\n".join(trek.get("images", [])))
                submitted = st.form_submit_button("Save Changes")
                if submitted:
                    events[i] = {
                        "name": name,
                        "image": image,
                        "location": location,
                        "date": date,
                        "difficulty": difficulty,
                        "organiser": organiser,
                        "phone": phone,
                        "price": price,
                        "intro": intro,
                        "about_trek": about_trek,
                        "detailed_schedule": detailed_schedule,
                        "key_highlights": [s.strip() for s in key_highlights.splitlines() if s.strip()],
                        "inclusions": [s.strip() for s in inclusions.splitlines() if s.strip()],
                        "exclusions": [s.strip() for s in exclusions.splitlines() if s.strip()],
                        "images": [s.strip() for s in gallery.splitlines() if s.strip()]
                    }
                    save_events(events)
                    st.success("Saved changes.")
                    del st.session_state["edit_index"]
                    st.rerun()
        else:
            st.info("No trek selected to edit.")
            if "edit_index" in st.session_state:
                del st.session_state["edit_index"]


# ---------------- Login page ----------------
def login_page():
    st.title("🔐 Login to Event Planner")
    st.write("Please enter your credentials to continue.")

    username = st.text_input("Username", key="login_username_main")
    password = st.text_input("Password", type="password", key="login_password_main")

    if st.button("Login", key="login_button_main"):
        do_login(username, password)


# ---------------- Main Flow ----------------
def main():
    events = load_events()

    # --- If not logged in, show login page ---
    if not st.session_state.get("logged_in", False):
        login_page()
        return

    # --- If Admin Logged In ---
    if st.session_state.get("role") == "admin":
        choice = admin_sidebar()

        if choice == "Dashboard":
            st.title("🔐 Admin Dashboard")
            st.write("Welcome, Admin! Manage your trek events below.")
            admin_dashboard(events)

        elif choice == "Add Trek":
            add_trek_page(events)

        elif choice == "Manage Treks":
            manage_treks_page(events)

    # --- If User Logged In ---
    elif st.session_state.get("role") == "user":
        page = user_sidebar()

        if page == "🚩 Maharashtra Treks":
            st.header("🚩 Treks in Maharashtra")
            show_trek_cards(events)

        elif page == "🌍 Outside Maharashtra":
            st.header("🌍 Treks Outside Maharashtra")
            st.info("No data added yet — Coming soon!")

        elif page == "📷 Gallery":
            st.header("📷 Trek Gallery")
            st.info("Gallery section coming soon!")

        elif page == "📞 Contact":
            st.header("📞 Contact Us")
            st.write("For trek details or custom group treks, reach us at:")
            st.write("📞 +91 7558783213 | 📧 info@vedhtreks.in")

        else:
            # simple user page
            st.title("🥾 Maharashtra Treks Explorer")
            st.write(f"Welcome, **{st.session_state.get('username','Guest')}** 👋")
            st.sidebar.subheader("Navigation")
            choice = st.sidebar.radio("Menu", ["View Treks", "Logout"])
            if choice == "View Treks":
                if events:
                    show_trek_cards(events)
                else:
                    st.info("No treks available at the moment.")
            else:
                do_logout()


if __name__ == "__main__":
    main()


# ---------------- Footer ----------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("© 2025 Vedh Girishikhranche | Adventure Awaits 🌄", unsafe_allow_html=True)


# ---- Clean hide for Streamlit branding ----
hide_st_style = """
    <style>
    /* Hide Streamlit's default menu and footer text */
    #MainMenu {display: none;}
    footer {display: none;}

    /* Hide Streamlit logo but keep header so toggle still works */
    [data-testid="stLogo"] {display: none !important;}

    /* Optional: adjust spacing under the header */
    [data-testid="stSidebarNav"] {margin-top: 1rem;}
    </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)























