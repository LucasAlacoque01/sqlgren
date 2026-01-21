 WITH criancas_covid AS (
    SELECT DISTINCT
        pec.co_seq_fat_cidadao_pec AS co_cidadao
    FROM tb_fat_vacinacao_vacina v
        JOIN tb_fat_vacinacao fv ON v.co_fat_vacinacao = fv.co_seq_fat_vacinacao
        JOIN tb_dim_imunobiologico i ON v.co_dim_imunobiologico = i.co_seq_dim_imunobiologico
        JOIN tb_imunobiologico ti ON i.nu_identificador = ti.co_imunobiologico::text
        JOIN tb_dim_tempo t ON v.co_dim_tempo = t.co_seq_dim_tempo
        JOIN tb_fat_cidadao_pec pec ON fv.co_fat_cidadao_pec = pec.co_seq_fat_cidadao_pec
    WHERE ti.st_covid = 1
      AND EXTRACT(YEAR FROM t.dt_registro) IN (2024, 2025)
),
criancas_faixa_etaria AS (
    SELECT 
        pec.co_seq_fat_cidadao_pec,
        pec.nu_cns,
        pec.nu_cpf_cidadao,
        pec.no_cidadao,
        ds.ds_sexo,
        dt.dt_registro AS dt_nascimento,
        EXTRACT(YEAR FROM age(current_date, dt.dt_registro))::integer AS idade_anos,
        (EXTRACT(MONTH FROM age(current_date, dt.dt_registro))::integer % 12) AS idade_meses,
        tdus.nu_cnes,
        tdus.no_unidade_saude,
        tde.nu_ine,
        tde.no_equipe
    FROM tb_fat_cidadao_pec pec
        JOIN tb_fat_cidadao_territorio fct ON pec.co_seq_fat_cidadao_pec = fct.co_fat_cidadao_pec
        JOIN tb_cidadao_vinculacao_equipe cve ON pec.co_cidadao = cve.co_cidadao
        JOIN tb_dim_tempo dt ON pec.co_dim_tempo_nascimento = dt.co_seq_dim_tempo
        JOIN tb_dim_sexo ds ON pec.co_dim_sexo = ds.co_seq_dim_sexo
        JOIN tb_dim_unidade_saude tdus ON cve.nu_cnes = tdus.nu_cnes 
        JOIN tb_dim_equipe tde ON cve.nu_ine = tde.nu_ine 
    WHERE fct.st_mudou_se = 0 
      AND fct.st_vivo = 1
      AND dt.dt_registro BETWEEN '2020-01-01' AND '2024-06-30'
     
)
SELECT 
    cf.nu_cnes,
    cf.no_unidade_saude,
    cf.nu_ine,
    cf.no_equipe,
    cf.nu_cns,
    cf.nu_cpf_cidadao,
    cf.no_cidadao,
    cf.ds_sexo,
    cf.dt_nascimento,
    CASE
        WHEN cf.idade_anos < 1 THEN cf.idade_meses || ' mes(es)'
        WHEN cf.idade_anos = 1 THEN '1 ano e ' || cf.idade_meses || ' mes(es)'
        ELSE cf.idade_anos || ' anos'
    END AS idade,
    'Faltoso COVID-19 (2024-2025)' AS observacao,
    current_date AS data_geracao_relatorio
FROM criancas_faixa_etaria cf
LEFT JOIN criancas_covid cc ON cf.co_seq_fat_cidadao_pec = cc.co_cidadao
WHERE cc.co_cidadao IS NULL
ORDER BY cf.no_unidade_saude, cf.nu_cnes, cf.no_equipe, cf.nu_ine, cf.no_cidadao;
