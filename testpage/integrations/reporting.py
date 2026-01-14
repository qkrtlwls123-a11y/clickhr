from io import BytesIO


def build_pptx_report(title, summary_lines, highlights):
    from pptx import Presentation
    from pptx.util import Inches, Pt

    presentation = Presentation()
    presentation.slide_width = Inches(13.33)
    presentation.slide_height = Inches(7.5)

    title_slide = presentation.slides.add_slide(presentation.slide_layouts[0])
    title_placeholder = title_slide.shapes.title
    subtitle_placeholder = title_slide.placeholders[1]

    title_placeholder.text = title
    subtitle_placeholder.text = "Click Insight Hub | HR Analytics"

    summary_slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    summary_title = summary_slide.shapes.title
    summary_title.text = "Executive Summary"

    left = Inches(1)
    top = Inches(1.8)
    width = Inches(11.5)
    height = Inches(4.5)
    textbox = summary_slide.shapes.add_textbox(left, top, width, height)
    text_frame = textbox.text_frame
    text_frame.word_wrap = True

    for line in summary_lines:
        paragraph = text_frame.add_paragraph()
        paragraph.text = line
        paragraph.font.size = Pt(18)

    highlight_slide = presentation.slides.add_slide(presentation.slide_layouts[5])
    highlight_title = highlight_slide.shapes.title
    highlight_title.text = "Highlights"

    h_left = Inches(1)
    h_top = Inches(1.8)
    h_width = Inches(11.5)
    h_height = Inches(4.5)
    highlight_box = highlight_slide.shapes.add_textbox(h_left, h_top, h_width, h_height)
    highlight_frame = highlight_box.text_frame

    for highlight in highlights:
        paragraph = highlight_frame.add_paragraph()
        paragraph.text = highlight
        paragraph.level = 0
        paragraph.font.size = Pt(18)

    output = BytesIO()
    presentation.save(output)
    output.seek(0)
    return output.getvalue()
