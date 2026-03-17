"""SQL queries for HRMS employee and pay scheme endpoints."""
from sqlalchemy import text


# ─── Employee queries ───────────────────────────────────────────────

def get_employee_list(branch_ids=None):
    branch_filter = "p.branch_id = :branch_id"
    if branch_ids:
        placeholders = ",".join(str(int(b)) for b in branch_ids)
        branch_filter = f"p.branch_id IN ({placeholders})"
    return text(f"""
        SELECT
            p.eb_id,
            p.first_name,
            p.middle_name,
            p.last_name,
            CONCAT(p.first_name, ' ', COALESCE(p.middle_name, ''), ' ', COALESCE(p.last_name, '')) AS full_name,
            p.email_id,
            p.gender,
            p.date_of_birth,
            p.pan_no,
            p.aadhar_no,
            p.mobile_no,
            p.status_id,
            s.status_name,
            p.active,
            o.emp_code,
            o.date_of_join,
            o.sub_dept_id,
            o.designation_id,
            o.branch_id,
            CONCAT(sd.sub_dept_desc, ' (', COALESCE(d.dept_desc, ''), ')') AS sub_dept_name,
            des.desig AS designation_name,
            b.branch_name,
            COALESCE(p.mobile_no, c.mobile_no) AS mobile_no
        FROM hrms_ed_personal_details p
        LEFT JOIN hrms_ed_official_details o ON o.eb_id = p.eb_id AND o.active = 1
        LEFT JOIN sub_dept_mst sd ON sd.sub_dept_id = o.sub_dept_id
        LEFT JOIN dept_mst d ON d.dept_id = sd.dept_id
        LEFT JOIN designation_mst des ON des.designation_id = o.designation_id
        LEFT JOIN branch_mst b ON b.branch_id = o.branch_id
        LEFT JOIN hrms_ed_contact_details c ON c.eb_id = p.eb_id AND c.active = 1
        LEFT JOIN status_mst s ON s.status_id = p.status_id
        WHERE {branch_filter}
          AND p.active = 1
          AND (:search IS NULL OR p.first_name LIKE :search
               OR p.last_name LIKE :search
               OR o.emp_code LIKE :search
               OR p.email_id LIKE :search)
          AND (:status_id IS NULL OR p.status_id = :status_id)
          AND (:sub_dept_id IS NULL OR o.sub_dept_id = :sub_dept_id)
        ORDER BY p.eb_id DESC
        LIMIT :page_size OFFSET :offset
    """)


def get_employee_list_count(branch_ids=None):
    branch_filter = "p.branch_id = :branch_id"
    if branch_ids:
        placeholders = ",".join(str(int(b)) for b in branch_ids)
        branch_filter = f"p.branch_id IN ({placeholders})"
    return text(f"""
        SELECT COUNT(*) AS total
        FROM hrms_ed_personal_details p
        LEFT JOIN hrms_ed_official_details o ON o.eb_id = p.eb_id AND o.active = 1
        WHERE {branch_filter}
          AND p.active = 1
          AND (:search IS NULL OR p.first_name LIKE :search
               OR p.last_name LIKE :search
               OR o.emp_code LIKE :search
               OR p.email_id LIKE :search)
          AND (:status_id IS NULL OR p.status_id = :status_id)
          AND (:sub_dept_id IS NULL OR o.sub_dept_id = :sub_dept_id)
    """)


def get_employee_personal_by_id():
    return text("""
        SELECT p.eb_id, p.first_name, p.middle_name, p.last_name, p.gender,
               p.date_of_birth, p.blood_group, p.mobile_no, p.email_id,
               p.marital_status, p.country_id, p.relegion_name, p.fixed_eb_id,
               p.father_spouse_name, p.passport_no, p.driving_licence_no,
               p.pan_no, p.aadhar_no, p.branch_id, p.updated_by, p.updated_date_time,
               p.active, p.status_id,
               CASE WHEN p.face_image IS NOT NULL THEN 1 ELSE 0 END AS has_photo
        FROM hrms_ed_personal_details p
        WHERE p.eb_id = :eb_id AND p.branch_id = :branch_id AND p.active = 1
    """)


def get_employee_contact_by_eb_id():
    return text("""
        SELECT * FROM hrms_ed_contact_details
        WHERE eb_id = :eb_id AND active = 1
    """)


def get_employee_address_by_eb_id():
    return text("""
        SELECT * FROM hrms_ed_address_details
        WHERE eb_id = :eb_id AND active = 1
    """)


def get_employee_official_by_eb_id():
    return text("""
        SELECT o.*,
               CONCAT(sd.sub_dept_desc, ' (', COALESCE(d.dept_desc, ''), ')') AS sub_dept_name,
               des.desig AS designation_name,
               b.branch_name,
               CONCAT(rp.first_name, ' ', COALESCE(rp.last_name, '')) AS reporting_to_name
        FROM hrms_ed_official_details o
        LEFT JOIN sub_dept_mst sd ON sd.sub_dept_id = o.sub_dept_id
        LEFT JOIN dept_mst d ON d.dept_id = sd.dept_id
        LEFT JOIN designation_mst des ON des.designation_id = o.designation_id
        LEFT JOIN branch_mst b ON b.branch_id = o.branch_id
        LEFT JOIN hrms_ed_personal_details rp ON rp.eb_id = o.reporting_eb_id
        WHERE o.eb_id = :eb_id AND o.active = 1
    """)


def get_employee_bank_by_eb_id():
    return text("""
        SELECT * FROM hrms_ed_bank_details
        WHERE eb_id = :eb_id AND active = 1
    """)


def get_employee_pf_by_eb_id():
    return text("""
        SELECT * FROM hrms_ed_pf
        WHERE eb_id = :eb_id AND active = 1
    """)


def get_employee_esi_by_eb_id():
    return text("""
        SELECT * FROM hrms_ed_esi
        WHERE eb_id = :eb_id AND active = 1
    """)


def get_employee_experience_by_eb_id():
    return text("""
        SELECT * FROM hrms_experience_details
        WHERE eb_id = :eb_id AND active = 1
    """)


def get_employee_resign_by_eb_id():
    return text("""
        SELECT * FROM hrms_ed_resign_details
        WHERE eb_id = :eb_id AND active = 1
    """)


def get_employee_create_setup():
    """Fetches all dropdown master data needed for employee creation (except designations which depend on branch)."""
    return text("""
        SELECT 'blood_groups' AS source, blood_group_id AS id, blood_group_name AS name FROM hrms_blood_group
        UNION ALL
        SELECT 'sub_departments', sd.sub_dept_id, CONCAT(sd.sub_dept_desc, ' (', COALESCE(d.dept_desc, ''), ')') FROM sub_dept_mst sd LEFT JOIN dept_mst d ON d.dept_id = sd.dept_id WHERE (:branch_id IS NULL OR d.branch_id = :branch_id)
        UNION ALL
        SELECT 'branches', branch_id, branch_name FROM branch_mst WHERE co_id = :co_id AND active = 1
        UNION ALL
        SELECT 'categories', cata_id, cata_desc FROM category_mst WHERE (:branch_id IS NULL OR branch_id = :branch_id)
        UNION ALL
        SELECT 'contractors', cont_id, contractor_name FROM contractor_mst WHERE (:branch_id IS NULL OR branch_id = :branch_id)
    """)


def get_designations_by_branch():
    """Fetches designations filtered by branch_id."""
    return text("""
        SELECT designation_id, desig
        FROM designation_mst
        WHERE branch_id = :branch_id AND active = 1
        ORDER BY desig
    """)


def get_reporting_employees():
    return text("""
        SELECT p.eb_id AS id,
               CONCAT(p.first_name, ' ', COALESCE(p.last_name, '')) AS name,
               o.emp_code
        FROM hrms_ed_personal_details p
        LEFT JOIN hrms_ed_official_details o ON o.eb_id = p.eb_id AND o.active = 1
        WHERE p.branch_id = :branch_id AND p.active = 1 AND p.status_id != 6
        ORDER BY p.first_name
    """)


# ─── Pay Scheme queries ────────────────────────────────────────────

def get_pay_scheme_list():
    return text("""
        SELECT
            ps.ID AS id,
            ps.CODE AS code,
            ps.NAME AS name,
            ps.DESCRIPTION AS description,
            ps.STATUS AS status_id,
            s.status_name,
            ps.EFFECTIVE_FROM AS effective_from,
            ps.ENDS_ON AS ends_on,
            (SELECT COUNT(*) FROM pay_employee_payscheme ep
             WHERE ep.PAY_SCHEME_ID = ps.ID AND ep.STATUS = 1) AS employee_count
        FROM pay_components ps
        LEFT JOIN status_mst s ON s.status_id = ps.STATUS
        WHERE ps.company_id = :co_id
          AND ps.TYPE = 0
          AND (:search IS NULL OR ps.NAME LIKE :search OR ps.CODE LIKE :search)
        ORDER BY ps.ID DESC
        LIMIT :page_size OFFSET :offset
    """)


def get_pay_scheme_by_id():
    return text("""
        SELECT
            ps.ID AS id,
            ps.CODE AS code,
            ps.NAME AS name,
            ps.DESCRIPTION AS description,
            ps.TYPE AS type,
            ps.STATUS AS status_id,
            ps.EFFECTIVE_FROM AS effective_from,
            ps.ENDS_ON AS ends_on,
            ps.DEFAULT_VALUE AS default_value,
            ps.PARENT_ID AS parent_id,
            ps.IS_CUSTOM_COMPONENT AS is_custom_component,
            ps.IS_DISPLAYABLE_IN_PAYSLIP AS is_displayable_in_payslip,
            ps.ROUNDOF AS roundof
        FROM pay_components ps
        WHERE ps.ID = :id AND ps.company_id = :co_id
    """)


def get_pay_scheme_components():
    return text("""
        SELECT
            pc.ID AS id,
            pc.CODE AS code,
            pc.NAME AS name,
            pc.TYPE AS type,
            pc.DEFAULT_VALUE AS default_value,
            pc.PARENT_ID AS parent_id,
            pc.IS_CUSTOM_COMPONENT AS is_custom_component,
            pc.IS_DISPLAYABLE_IN_PAYSLIP AS is_displayable_in_payslip
        FROM pay_components pc
        WHERE pc.company_id = :co_id
          AND pc.STATUS = 1
          AND pc.TYPE IN (1, 2, 3)
        ORDER BY pc.TYPE, pc.NAME
    """)


def get_pay_scheme_create_setup():
    return text("""
        SELECT
            pc.ID AS id,
            pc.CODE AS code,
            pc.NAME AS name,
            pc.TYPE AS type,
            pc.DEFAULT_VALUE AS default_value,
            pc.IS_CUSTOM_COMPONENT AS is_custom_component
        FROM pay_components pc
        WHERE pc.company_id = :co_id
          AND pc.STATUS = 1
        ORDER BY pc.TYPE, pc.NAME
    """)


# ─── Pay Param (pay period) queries ────────────────────────────────

def get_pay_param_list():
    return text("""
        SELECT
            pp.ID AS id,
            pp.FROM_DATE AS from_date,
            pp.TO_DATE AS to_date,
            pp.PAYSCHEME_ID AS payscheme_id,
            pp.STATUS AS status_id,
            s.status_name,
            pp.branch_id,
            ps.NAME AS scheme_name,
            b.branch_name
        FROM pay_period pp
        LEFT JOIN pay_components ps ON ps.ID = pp.PAYSCHEME_ID
        LEFT JOIN branch_mst b ON b.branch_id = pp.branch_id
        LEFT JOIN status_mst s ON s.status_id = pp.STATUS
        WHERE ps.company_id = :co_id
          AND (:search IS NULL OR ps.NAME LIKE :search)
        ORDER BY pp.ID DESC
        LIMIT :page_size OFFSET :offset
    """)


# ─── Employee Photo queries (stored in hrms_ed_personal_details) ────

def get_employee_photo_by_eb_id():
    return text("""
        SELECT eb_id, face_image, file_name, file_extension
        FROM hrms_ed_personal_details
        WHERE eb_id = :eb_id
          AND face_image IS NOT NULL
        LIMIT 1
    """)


def upsert_employee_photo():
    return text("""
        UPDATE hrms_ed_personal_details
        SET face_image = :face_image,
            file_name = :file_name,
            file_extension = :file_extension,
            updated_by = :updated_by
        WHERE eb_id = :eb_id
    """)


def delete_employee_photo():
    return text("""
        UPDATE hrms_ed_personal_details
        SET face_image = NULL,
            file_name = NULL,
            file_extension = NULL
        WHERE eb_id = :eb_id
    """)
