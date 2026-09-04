-- Resumo: Consulta de hipertensão (tabelas: TB_DIM_TEMPO, TB_FAT_PROCED_ATEND_PROCED, TB_DIM_PROCEDIMENTO, TB_DIM_CBO, PACIENTES_HIPERTENSOS, TB_FAT_ATD_IND_PROBLEMAS, TB_DIM_CIAP)
-- Nº Total de Hipertensos com PA Aferida (Médico ou Enfermeiro)

WITH pacientes_hipertensos AS (
    SELECT DISTINCT FAIP.CO_FAT_CIDADAO_PEC
    FROM TB_FAT_ATD_IND_PROBLEMAS FAIP
    JOIN TB_DIM_CIAP CIAP ON FAIP.CO_DIM_CIAP = CIAP.CO_SEQ_DIM_CIAP
    WHERE CIAP.NU_CIAP IN ('K86', 'K87', 'ABP005')
)
SELECT COUNT(DISTINCT pr.co_fat_cidadao_pec) AS "Nº de Hipertensos com PA Aferida"
FROM tb_fat_proced_atend_proced pr
JOIN tb_dim_tempo tdt ON pr.co_dim_tempo = tdt.co_seq_dim_tempo
JOIN tb_dim_procedimento proc ON pr.co_dim_procedimento = proc.co_seq_dim_procedimento
JOIN tb_dim_cbo tdc ON pr.co_dim_cbo = tdc.co_seq_dim_cbo
WHERE tdt.nu_ano = '2025'
    AND tdt.nu_mes = '7'
    AND pr.co_fat_cidadao_pec IN (
        SELECT CO_FAT_CIDADAO_PEC
        FROM pacientes_hipertensos
    )
    AND proc.co_proced IN ('0301100039', 'ABPG033')
    AND (
        tdc.nu_cbo::text LIKE '225%' -- Médicos
        OR tdc.nu_cbo::text LIKE '2235%' -- Enfermeiros 
        );