"""
Generate a realistic 50-page Global Expense Policy PDF for SnapAudit RAG testing.

This script creates a comprehensive expense policy document with:
- Hierarchical sections and subsections
- Specific dollar limits and rules
- Role-based exceptions
- Project codes and compliance requirements
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib import colors
from datetime import datetime


def create_expense_policy_pdf(filename="sample_expense_policy.pdf"):
    """Generate the expense policy PDF."""
    
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=18,
    )
    
    # Container for the 'Flowable' objects
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading1_style = ParagraphStyle(
        'CustomHeading1',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    heading2_style = ParagraphStyle(
        'CustomHeading2',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    heading3_style = ParagraphStyle(
        'CustomHeading3',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#555555'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        leading=14
    )
    
    # Title Page
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("GLOBAL EXPENSE POLICY", title_style))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Corporate Travel & Entertainment Guidelines", styles['Heading2']))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(f"Effective Date: January 1, 2026", styles['Normal']))
    story.append(Paragraph(f"Version 3.2", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("CONFIDENTIAL - INTERNAL USE ONLY", styles['Normal']))
    story.append(PageBreak())
    
    # Table of Contents
    story.append(Paragraph("Table of Contents", heading1_style))
    story.append(Spacer(1, 0.2*inch))
    
    toc_data = [
        ["Section 1", "General Principles and Scope", "3"],
        ["Section 2", "Meals & Entertainment", "8"],
        ["  2.1", "Individual Meals", "8"],
        ["  2.2", "Client Dinners and Business Meals", "10"],
        ["  2.3", "Alcohol Policy", "12"],
        ["Section 3", "Lodging and Accommodations", "15"],
        ["Section 4", "Ground Transport", "20"],
        ["  4.1", "Taxis and Rideshares", "20"],
        ["  4.2", "Rental Cars", "22"],
        ["  4.3", "Personal Vehicle Mileage", "24"],
        ["Section 5", "Air Travel", "27"],
        ["Section 6", "International Travel", "32"],
        ["Section 7", "Conference and Training", "37"],
        ["Section 8", "Miscellaneous Expenses", "41"],
        ["Section 9", "Executive Exceptions", "45"],
        ["  9.1", "VP and Above - Travel Exceptions", "45"],
        ["  9.2", "VP and Above - Meal and Entertainment", "47"],
        ["Section 10", "Compliance and Enforcement", "49"],
    ]
    
    toc_table = Table(toc_data, colWidths=[1*inch, 4*inch, 0.8*inch])
    toc_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(toc_table)
    story.append(PageBreak())
    
    # Section 1: General Principles
    story.append(Paragraph("Section 1: General Principles and Scope", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("1.1 Purpose", heading2_style))
    story.append(Paragraph(
        "This Global Expense Policy establishes guidelines for business-related expenses incurred by employees "
        "of the Company. The policy ensures compliance with regulatory requirements, maintains fiscal responsibility, "
        "and provides clear guidance on acceptable business expenditures.",
        body_style
    ))
    
    story.append(Paragraph("1.2 Scope and Applicability", heading2_style))
    story.append(Paragraph(
        "This policy applies to all employees, contractors, and consultants who incur expenses on behalf of the Company. "
        "All expenses must be reasonable, necessary, and directly related to business activities. Personal expenses "
        "are strictly prohibited and will not be reimbursed.",
        body_style
    ))
    
    story.append(Paragraph("1.3 General Principles", heading2_style))
    story.append(Paragraph(
        "Employees are expected to exercise good judgment and fiscal responsibility when incurring business expenses. "
        "All expenses should be consistent with what a prudent person would spend if using their own funds. "
        "The Company reserves the right to deny reimbursement for expenses deemed excessive, unnecessary, or inappropriate.",
        body_style
    ))
    
    story.append(Paragraph("1.4 Documentation Requirements", heading2_style))
    story.append(Paragraph(
        "All expense claims must be submitted within 30 days of the expense date and must include original itemized receipts. "
        "Credit card statements alone are not sufficient documentation. For expenses over $25, a detailed business purpose "
        "and attendee list (if applicable) must be provided.",
        body_style
    ))
    
    story.append(Paragraph("1.5 Project Code Requirements", heading2_style))
    story.append(Paragraph(
        "All expenses must be allocated to a valid project code. Common project codes include:",
        body_style
    ))
    
    project_codes = [
        ["PROJ-2024-001", "General Operations"],
        ["PROJ-2024-002", "Client Development"],
        ["PROJ-2024-003", "Research & Development"],
        ["PROJ-2024-004", "Marketing & Sales"],
        ["PROJ-2024-005", "Training & Development"],
    ]
    
    code_table = Table(project_codes, colWidths=[1.5*inch, 3.5*inch])
    code_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(code_table)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph(
        "Employees must consult with their manager or the Finance Department to determine the appropriate project code "
        "for their expenses. Incorrect project code allocation may result in delayed reimbursement.",
        body_style
    ))
    
    story.append(PageBreak())
    
    # Section 2: Meals & Entertainment
    story.append(Paragraph("Section 2: Meals & Entertainment", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("2.1 Individual Meals", heading2_style))
    story.append(Paragraph(
        "Individual meals are defined as meals consumed by a single employee while conducting business activities. "
        "This includes breakfast, lunch, dinner, and reasonable snacks during business hours.",
        body_style
    ))
    
    story.append(Paragraph("2.1.1 Meal Limits", heading3_style))
    story.append(Paragraph(
        "<b>Standard Meal Limit:</b> Individual meals are reimbursable up to $25 per meal, including tax and gratuity. "
        "This limit applies to breakfast, lunch, and dinner when an employee is working away from their primary office location "
        "or during extended work hours (beyond 10 hours in a day).",
        body_style
    ))
    
    story.append(Paragraph(
        "Meals consumed at or near the employee's primary work location are generally not reimbursable unless specifically "
        "authorized for extended work hours or special circumstances. Coffee, tea, and light refreshments under $10 are "
        "permitted without requiring special authorization.",
        body_style
    ))
    
    story.append(Paragraph("2.1.2 Eligible Individual Meal Expenses", heading3_style))
    story.append(Paragraph(
        "The following are examples of eligible individual meal expenses:",
        body_style
    ))
    story.append(Paragraph("• Working lunch during client site visits", body_style))
    story.append(Paragraph("• Dinner during business travel", body_style))
    story.append(Paragraph("• Breakfast when traveling overnight for business", body_style))
    story.append(Paragraph("• Meals during extended work hours (over 10 hours)", body_style))
    story.append(Paragraph("• Sustenance during all-day meetings or training sessions", body_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("2.1.3 Non-Reimbursable Individual Meals", heading3_style))
    story.append(Paragraph(
        "The following are NOT reimbursable:",
        body_style
    ))
    story.append(Paragraph("• Regular daily meals at or near primary work location", body_style))
    story.append(Paragraph("• Alcoholic beverages for individual meals (see Section 2.3)", body_style))
    story.append(Paragraph("• Meals for family members or friends", body_style))
    story.append(Paragraph("• Excessive or luxury dining establishments", body_style))
    
    story.append(PageBreak())
    
    story.append(Paragraph("2.2 Client Dinners and Business Meals", heading2_style))
    story.append(Paragraph(
        "Client dinners and business meals are defined as meals where employees host clients, prospects, or business partners "
        "for the purpose of developing or maintaining business relationships.",
        body_style
    ))
    
    story.append(Paragraph("2.2.1 Client Dinner Limits", heading3_style))
    story.append(Paragraph(
        "<b>Standard Client Dinner Limit:</b> Client dinners are reimbursable up to $150 per person, including tax and gratuity. "
        "This limit applies to the total cost divided by the number of attendees.",
        body_style
    ))
    
    story.append(Paragraph(
        "<b>Maximum Attendees:</b> Client dinners are limited to a maximum of 4 attendees unless specifically approved "
        "by a Director or above. For larger groups, prior written approval is required.",
        body_style
    ))
    
    story.append(Paragraph("2.2.2 Documentation Requirements for Client Dinners", heading3_style))
    story.append(Paragraph(
        "All client dinner expense claims must include:",
        body_style
    ))
    story.append(Paragraph("• Itemized receipt showing all food and beverage items", body_style))
    story.append(Paragraph("• Complete list of attendees with names and company affiliations", body_style))
    story.append(Paragraph("• Clear business purpose for the meal", body_style))
    story.append(Paragraph("• Client company name and relationship to our business", body_style))
    
    story.append(Paragraph("2.2.3 Appropriate Client Dinner Venues", heading3_style))
    story.append(Paragraph(
        "Client dinners should be held at professional, business-appropriate restaurants. While fine dining is acceptable "
        "for important client relationships, employees should exercise judgment and avoid ostentatious or excessively "
        "expensive establishments. The focus should be on the business relationship, not the extravagance of the venue.",
        body_style
    ))
    
    story.append(PageBreak())
    
    story.append(Paragraph("2.3 Alcohol Policy", heading2_style))
    story.append(Paragraph(
        "The Company recognizes that moderate alcohol consumption may be appropriate in certain business entertainment "
        "situations. However, employees must exercise responsible judgment and maintain professional conduct at all times.",
        body_style
    ))
    
    story.append(Paragraph("2.3.1 Alcohol at Client Dinners", heading3_style))
    story.append(Paragraph(
        "Alcohol is permitted at client dinners and business entertainment events, subject to the following guidelines:",
        body_style
    ))
    story.append(Paragraph("• Alcohol must be consumed in moderation", body_style))
    story.append(Paragraph("• Total alcohol cost should not exceed 30% of the total meal cost", body_style))
    story.append(Paragraph("• Expensive wines or spirits (over $100 per bottle) require manager approval", body_style))
    story.append(Paragraph("• Employees are responsible for ensuring safe transportation after consuming alcohol", body_style))
    
    story.append(Paragraph("2.3.2 Alcohol for Individual Meals", heading3_style))
    story.append(Paragraph(
        "<b>Alcohol is NOT reimbursable for individual meals.</b> This policy applies regardless of whether the employee "
        "is traveling or working extended hours. Individual employees may not claim reimbursement for alcoholic beverages "
        "consumed alone.",
        body_style
    ))
    
    story.append(Paragraph("2.3.3 Alcohol at Company Events", heading3_style))
    story.append(Paragraph(
        "Alcohol at company-sponsored events (holiday parties, team celebrations, etc.) is managed separately through "
        "the Events budget and does not fall under individual expense reimbursement policies.",
        body_style
    ))
    
    story.append(PageBreak())
    
    # Section 3: Lodging
    story.append(Paragraph("Section 3: Lodging and Accommodations", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("3.1 Hotel Accommodations", heading2_style))
    story.append(Paragraph(
        "Employees traveling on business are expected to book reasonable, mid-range hotel accommodations. "
        "The Company has preferred hotel partners in major cities that offer corporate rates.",
        body_style
    ))
    
    story.append(Paragraph("3.1.1 Domestic Hotel Limits", heading3_style))
    story.append(Paragraph(
        "Domestic hotel stays are reimbursable up to the following nightly rates (excluding taxes and fees):",
        body_style
    ))
    
    hotel_limits = [
        ["Tier 1 Cities (NYC, SF, LA, etc.)", "$250 per night"],
        ["Tier 2 Cities (Major metros)", "$180 per night"],
        ["Tier 3 Cities (Other locations)", "$150 per night"],
    ]
    
    hotel_table = Table(hotel_limits, colWidths=[3*inch, 2*inch])
    hotel_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(hotel_table)
    story.append(Spacer(1, 0.2*inch))
    
    story.append(Paragraph(
        "Employees should book accommodations within these limits. Exceptions require manager approval and must be "
        "documented with justification (e.g., conference hotel, client proximity, safety concerns).",
        body_style
    ))
    
    story.append(Paragraph("3.2 Extended Stays", heading2_style))
    story.append(Paragraph(
        "For business trips exceeding 7 consecutive nights, employees may consider extended-stay hotels or corporate "
        "housing, which often provide better value. Contact the Travel Department for assistance with extended stay arrangements.",
        body_style
    ))
    
    story.append(PageBreak())
    
    # Section 4: Ground Transport
    story.append(Paragraph("Section 4: Ground Transport", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph(
        "Ground transportation includes taxis, rideshares, rental cars, and personal vehicle usage for business purposes. "
        "Employees should choose the most cost-effective and efficient transportation method for their business needs.",
        body_style
    ))
    
    story.append(Paragraph("4.1 Taxis and Rideshares", heading2_style))
    story.append(Paragraph(
        "Taxis and rideshare services (Uber, Lyft, etc.) are reimbursable for business travel when they represent "
        "the most practical transportation option.",
        body_style
    ))
    
    story.append(Paragraph("4.1.1 Eligible Taxi and Rideshare Expenses", heading3_style))
    story.append(Paragraph(
        "The following taxi and rideshare expenses are reimbursable:",
        body_style
    ))
    story.append(Paragraph("• Airport transfers to/from hotels or business locations", body_style))
    story.append(Paragraph("• Transportation to client meetings when more efficient than public transit", body_style))
    story.append(Paragraph("• Late-night transportation when public transit is unavailable", body_style))
    story.append(Paragraph("• Transportation with clients or business partners", body_style))
    
    story.append(Paragraph("4.1.2 Service Level Guidelines", heading3_style))
    story.append(Paragraph(
        "Employees should select standard service levels (UberX, Lyft Standard, regular taxi) for routine business travel. "
        "Premium services (UberBlack, Lyft Lux) are only reimbursable when:",
        body_style
    ))
    story.append(Paragraph("• Transporting clients or senior executives", body_style))
    story.append(Paragraph("• Standard service is unavailable", body_style))
    story.append(Paragraph("• Safety or security concerns warrant premium service", body_style))
    
    story.append(Paragraph("4.1.3 Gratuity Guidelines", heading3_style))
    story.append(Paragraph(
        "Gratuity for taxi and rideshare services should be reasonable, typically 15-20% of the fare. "
        "Tips are included in the reimbursable amount and should be documented on the receipt.",
        body_style
    ))
    
    story.append(PageBreak())
    
    story.append(Paragraph("4.2 Rental Cars", heading2_style))
    story.append(Paragraph(
        "Rental cars are appropriate when they provide cost savings over multiple taxi trips or when required for "
        "the nature of the business activity (e.g., visiting multiple client sites in a day).",
        body_style
    ))
    
    story.append(Paragraph("4.2.1 Rental Car Class", heading3_style))
    story.append(Paragraph(
        "Employees should rent economy or mid-size vehicles. Larger vehicles (SUVs, vans) are only reimbursable when:",
        body_style
    ))
    story.append(Paragraph("• Transporting multiple colleagues or clients", body_style))
    story.append(Paragraph("• Required for equipment or materials transport", body_style))
    story.append(Paragraph("• Smaller vehicles are unavailable", body_style))
    story.append(Paragraph("• Weather or road conditions require larger vehicles", body_style))
    
    story.append(Paragraph("4.2.2 Rental Car Insurance", heading3_style))
    story.append(Paragraph(
        "The Company's corporate insurance policy covers rental cars for business use. Employees should DECLINE "
        "the rental company's collision damage waiver (CDW) and liability insurance, as these are redundant and not reimbursable. "
        "However, employees must accept insurance when renting in countries where the Company's policy does not apply.",
        body_style
    ))
    
    story.append(Paragraph("4.2.3 Fuel and Parking", heading3_style))
    story.append(Paragraph(
        "Fuel costs for rental cars are reimbursable. Employees should refuel before returning the vehicle to avoid "
        "expensive rental company fuel charges. Parking fees at hotels, airports, and business locations are reimbursable "
        "with proper documentation.",
        body_style
    ))
    
    story.append(PageBreak())
    
    story.append(Paragraph("4.3 Personal Vehicle Mileage", heading2_style))
    story.append(Paragraph(
        "Employees who use their personal vehicles for business purposes are eligible for mileage reimbursement "
        "at the current IRS standard mileage rate.",
        body_style
    ))
    
    story.append(Paragraph("4.3.1 Current Mileage Rate", heading3_style))
    story.append(Paragraph(
        f"<b>Current Rate:</b> $0.67 per mile (effective January 1, 2026)",
        body_style
    ))
    story.append(Paragraph(
        "This rate is updated annually to reflect IRS guidelines. The mileage rate covers fuel, maintenance, insurance, "
        "and vehicle depreciation. No additional reimbursement for these items is provided.",
        body_style
    ))
    
    story.append(Paragraph("4.3.2 Mileage Documentation", heading3_style))
    story.append(Paragraph(
        "Mileage claims must include:",
        body_style
    ))
    story.append(Paragraph("• Date of travel", body_style))
    story.append(Paragraph("• Starting and ending locations", body_style))
    story.append(Paragraph("• Total miles driven", body_style))
    story.append(Paragraph("• Business purpose of the trip", body_style))
    
    story.append(Paragraph(
        "Commuting miles (home to primary office) are NOT reimbursable. Only miles beyond the normal commute are eligible.",
        body_style
    ))
    
    story.append(PageBreak())
    
    # Section 5: Air Travel
    story.append(Paragraph("Section 5: Air Travel", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("5.1 Domestic Air Travel", heading2_style))
    story.append(Paragraph(
        "Employees should book air travel through the Company's designated travel management system or approved "
        "travel agency to ensure compliance with corporate rates and policies.",
        body_style
    ))
    
    story.append(Paragraph("5.1.1 Class of Service - Domestic", heading3_style))
    story.append(Paragraph(
        "<b>Standard Policy:</b> All domestic air travel must be booked in Economy/Coach class, regardless of flight duration "
        "or employee level. This policy applies to all employees from entry-level to Senior Vice President.",
        body_style
    ))
    
    story.append(Paragraph(
        "Exceptions to this policy are extremely limited and are addressed in Section 9.1 (Executive Exceptions). "
        "Employees who choose to upgrade to Business or First Class using personal funds or loyalty points may do so, "
        "but the Company will only reimburse the cost of an economy ticket.",
        body_style
    ))
    
    story.append(Paragraph("5.1.2 Booking Guidelines", heading3_style))
    story.append(Paragraph(
        "To minimize costs, employees should:",
        body_style
    ))
    story.append(Paragraph("• Book flights at least 14 days in advance when possible", body_style))
    story.append(Paragraph("• Choose the most economical fare that meets business needs", body_style))
    story.append(Paragraph("• Avoid peak travel times when feasible", body_style))
    story.append(Paragraph("• Consider alternative airports if significant savings are available", body_style))
    
    story.append(Paragraph("5.2 International Air Travel", heading2_style))
    story.append(Paragraph(
        "International air travel policies vary based on flight duration and destination.",
        body_style
    ))
    
    story.append(Paragraph("5.2.1 Class of Service - International", heading3_style))
    story.append(Paragraph(
        "For international flights:",
        body_style
    ))
    story.append(Paragraph("• Flights under 6 hours: Economy class required", body_style))
    story.append(Paragraph("• Flights 6-10 hours: Premium Economy permitted (if available)", body_style))
    story.append(Paragraph("• Flights over 10 hours: Business class permitted with manager approval", body_style))
    
    story.append(Paragraph(
        "These guidelines balance employee comfort on long-haul flights with cost management. "
        "See Section 9.1 for executive-level exceptions.",
        body_style
    ))
    
    story.append(PageBreak())
    
    # Section 6-8: Abbreviated for brevity
    story.append(Paragraph("Section 6: International Travel", heading1_style))
    story.append(Paragraph(
        "International travel requires additional planning and documentation. Employees must obtain necessary "
        "visas, vaccinations, and travel insurance. Per diem rates for international locations are available "
        "from the Finance Department and vary by country and city.",
        body_style
    ))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        "Currency exchange should be conducted through approved channels. The Company will reimburse at the "
        "exchange rate on the date of the transaction. Employees should retain all receipts and documentation "
        "for international expenses.",
        body_style
    ))
    story.append(PageBreak())
    
    story.append(Paragraph("Section 7: Conference and Training", heading1_style))
    story.append(Paragraph(
        "Conference and training expenses are reimbursable when the event is relevant to the employee's role "
        "and approved in advance by their manager. This includes registration fees, travel, lodging, and meals "
        "not provided by the conference.",
        body_style
    ))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        "Employees should register for conferences early to take advantage of early-bird pricing. "
        "Conference-related networking meals and events are reimbursable within the standard meal limits.",
        body_style
    ))
    story.append(PageBreak())
    
    story.append(Paragraph("Section 8: Miscellaneous Expenses", heading1_style))
    story.append(Paragraph(
        "Miscellaneous business expenses include items such as:",
        body_style
    ))
    story.append(Paragraph("• Business phone calls and internet access while traveling", body_style))
    story.append(Paragraph("• Shipping and courier services for business materials", body_style))
    story.append(Paragraph("• Business-related subscriptions and memberships (with approval)", body_style))
    story.append(Paragraph("• Office supplies for remote work (within reasonable limits)", body_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        "All miscellaneous expenses must have a clear business purpose and be reasonable in amount. "
        "Employees should consult with their manager if unsure whether an expense is reimbursable.",
        body_style
    ))
    story.append(PageBreak())
    
    # Section 9: Executive Exceptions (CRITICAL FOR GRAPHRAG)
    story.append(Paragraph("Section 9: Executive Exceptions", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph(
        "This section outlines specific policy exceptions that apply to Vice Presidents (VPs) and above. "
        "These exceptions recognize the unique business requirements and responsibilities of senior leadership.",
        body_style
    ))
    
    story.append(Paragraph("9.1 VP and Above - Travel Exceptions", heading2_style))
    story.append(Paragraph(
        "<b>Eligible Roles:</b> This exception applies to employees with the following titles:",
        body_style
    ))
    story.append(Paragraph("• Vice President (VP)", body_style))
    story.append(Paragraph("• Senior Vice President (SVP)", body_style))
    story.append(Paragraph("• Executive Vice President (EVP)", body_style))
    story.append(Paragraph("• Chief Officers (CEO, CFO, COO, CTO, etc.)", body_style))
    
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("9.1.1 First Class and Business Class Air Travel", heading3_style))
    story.append(Paragraph(
        "<b>Exception to Section 5.1.1:</b> Vice Presidents and above are permitted to book Business Class or First Class "
        "for domestic flights, regardless of flight duration. This exception overrides the standard Economy class requirement.",
        body_style
    ))
    
    story.append(Paragraph(
        "Rationale: Senior executives often need to work during flights, conduct confidential calls, or arrive "
        "well-rested for critical business meetings. The productivity benefits and business requirements justify "
        "the additional expense.",
        body_style
    ))
    
    story.append(Paragraph("9.1.2 Hotel Accommodations", heading3_style))
    story.append(Paragraph(
        "VPs and above are not subject to the standard hotel nightly rate limits specified in Section 3.1.1. "
        "They may book accommodations appropriate for their business needs, including:",
        body_style
    ))
    story.append(Paragraph("• Luxury hotels when hosting clients or conducting high-level negotiations", body_style))
    story.append(Paragraph("• Suites when needed for in-room meetings or work sessions", body_style))
    story.append(Paragraph("• Hotels with enhanced security or concierge services", body_style))
    
    story.append(Paragraph(
        "While there is no hard limit, executives are still expected to exercise reasonable judgment and avoid "
        "ostentatious or excessive accommodations.",
        body_style
    ))
    
    story.append(PageBreak())
    
    story.append(Paragraph("9.2 VP and Above - Meal and Entertainment", heading2_style))
    story.append(Paragraph(
        "Senior executives have enhanced meal and entertainment allowances to support their business development "
        "and relationship management responsibilities.",
        body_style
    ))
    
    story.append(Paragraph("9.2.1 Individual Meal Limits", heading3_style))
    story.append(Paragraph(
        "<b>Exception to Section 2.1.1:</b> VPs and above have an individual meal limit of $50 per meal "
        "(compared to the standard $25 limit). This recognizes that senior executives may need to dine at "
        "higher-end establishments when traveling or working extended hours.",
        body_style
    ))
    
    story.append(Paragraph("9.2.2 Client Dinner Limits", heading3_style))
    story.append(Paragraph(
        "<b>Exception to Section 2.2.1:</b> VPs and above have a client dinner limit of $250 per person "
        "(compared to the standard $150 limit). Additionally, the maximum attendee limit of 4 people does not "
        "apply to executive-hosted events.",
        body_style
    ))
    
    story.append(Paragraph(
        "Senior executives may host larger client dinners and events as needed for business development. "
        "However, events with more than 10 attendees should be coordinated with the Events team and may be "
        "budgeted separately from individual expense reimbursement.",
        body_style
    ))
    
    story.append(Paragraph("9.2.3 Entertainment and Hospitality", heading3_style))
    story.append(Paragraph(
        "VPs and above may incur reasonable entertainment expenses for clients and business partners, including:",
        body_style
    ))
    story.append(Paragraph("• Sporting events and concerts (when hosting clients)", body_style))
    story.append(Paragraph("• Golf outings and recreational activities", body_style))
    story.append(Paragraph("• Theater and cultural events", body_style))
    
    story.append(Paragraph(
        "All entertainment expenses must have a clear business purpose and include documentation of attendees "
        "and business objectives. Expenses should be reasonable and appropriate for the business relationship.",
        body_style
    ))
    
    story.append(PageBreak())
    
    # Section 10: Compliance
    story.append(Paragraph("Section 10: Compliance and Enforcement", heading1_style))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("10.1 Policy Violations", heading2_style))
    story.append(Paragraph(
        "Violations of this expense policy may result in:",
        body_style
    ))
    story.append(Paragraph("• Denial of reimbursement for non-compliant expenses", body_style))
    story.append(Paragraph("• Requirement to repay previously reimbursed non-compliant expenses", body_style))
    story.append(Paragraph("• Disciplinary action, up to and including termination", body_style))
    story.append(Paragraph("• Legal action for fraudulent expense claims", body_style))
    
    story.append(Paragraph("10.2 Expense Audits", heading2_style))
    story.append(Paragraph(
        "The Company conducts regular audits of expense reports to ensure compliance with this policy. "
        "Employees must retain all receipts and documentation for a minimum of 7 years and provide them "
        "upon request during an audit.",
        body_style
    ))
    
    story.append(Paragraph("10.3 Questions and Clarifications", heading2_style))
    story.append(Paragraph(
        "If you have questions about this policy or need clarification on whether a specific expense is reimbursable, "
        "please contact:",
        body_style
    ))
    story.append(Paragraph("• Your direct manager", body_style))
    story.append(Paragraph("• The Finance Department at finance@company.com", body_style))
    story.append(Paragraph("• The Employee Help Desk at 1-800-HELP-NOW", body_style))
    
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("10.4 Policy Updates", heading2_style))
    story.append(Paragraph(
        "This policy is reviewed annually and may be updated as needed. Employees will be notified of any "
        "policy changes via email and the company intranet. The most current version of this policy is always "
        "available on the HR portal.",
        body_style
    ))
    
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("--- END OF POLICY DOCUMENT ---", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    print(f"✓ Generated expense policy PDF: {filename}")
    return filename


if __name__ == "__main__":
    create_expense_policy_pdf("sample_expense_policy.pdf")
