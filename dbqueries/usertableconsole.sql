CREATE TABLE con_role_menu_map (
    con_role_menu_mapping_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    con_role_id INT,
    con_menu_id INT,
    con_org_id INT, 
    FOREIGN KEY (con_role_id) REFERENCES con_role_master(con_role_id),
    FOREIGN KEY (con_menu_id) REFERENCES con_menu_master(con_menu_id),
    FOREIGN KEY (con_org_id) REFERENCES con_org_master(con_org_id)
);
