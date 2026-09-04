-- Resumo: Volume mensal de atendimentos por unidade e CBO
SELECT
    tdus.no_unidade_saude,
    tdc.no_cbo,
    tdt.nu_ano,
    tdt.nu_mes,
    COUNT(*) AS qtd_atendimentos,
    COUNT(DISTINCT pr.co_fat_cidadao_pec) AS cidadaos_unicos
FROM tb_fat_proced_atend_proced pr
JOIN tb_dim_tempo tdt ON pr.co_dim_tempo = tdt.co_seq_dim_tempo
JOIN tb_dim_cbo tdc ON pr.co_dim_cbo = tdc.co_seq_dim_cbo
JOIN tb_dim_unidade_saude tdus ON pr.co_dim_unidade_saude = tdus.co_seq_dim_unidade_saude
WHERE tdt.nu_ano = :ano
GROUP BY tdus.no_unidade_saude, tdc.no_cbo, tdt.nu_ano, tdt.nu_mes
ORDER BY qtd_atendimentos DESC;
