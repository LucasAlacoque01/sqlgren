-- Resumo: Diabéticos acompanhados com hemoglobina glicada no semestre
WITH diabeticos AS (
    SELECT DISTINCT faip.co_fat_cidadao_pec
    FROM tb_fat_atd_ind_problemas faip
    JOIN tb_dim_ciap ciap ON faip.co_dim_ciap = ciap.co_seq_dim_ciap
    WHERE ciap.nu_ciap IN ('T89', 'T90', 'ABP006')
)
SELECT
    tdus.no_unidade_saude,
    COUNT(DISTINCT pr.co_fat_cidadao_pec) AS diabeticos_com_hba1c,
    ROUND(100.0 * COUNT(DISTINCT pr.co_fat_cidadao_pec) / NULLIF(COUNT(DISTINCT d.co_fat_cidadao_pec), 0), 1) AS cobertura_pct,
    LAG(COUNT(DISTINCT pr.co_fat_cidadao_pec)) OVER (PARTITION BY tdus.no_unidade_saude ORDER BY tdt.nu_mes) AS mes_anterior
FROM diabeticos d
LEFT JOIN tb_fat_proced_atend_proced pr
    ON pr.co_fat_cidadao_pec = d.co_fat_cidadao_pec
LEFT JOIN tb_dim_tempo tdt ON pr.co_dim_tempo = tdt.co_seq_dim_tempo
LEFT JOIN tb_dim_procedimento proc ON pr.co_dim_procedimento = proc.co_seq_dim_procedimento
LEFT JOIN tb_dim_unidade_saude tdus ON pr.co_dim_unidade_saude = tdus.co_seq_dim_unidade_saude
WHERE tdt.nu_ano = :ano
  AND proc.co_proced IN ('0202010503', 'ABEX008')
GROUP BY tdus.no_unidade_saude, tdt.nu_mes
ORDER BY cobertura_pct DESC;
