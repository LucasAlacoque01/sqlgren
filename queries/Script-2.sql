select 
    cv.no_unidade_saude as "UNIDADE",
    cv.no_cidadao as "CIDADÃO",
    cv.nu_cpf as "CPF",
    cv.nu_cns as "CNS",
    to_char(cv.dt_nascimento, 'dd/MM/yyyy') as "DATA NASC",
    case
        when cv.idade_meses < 12 then 
            cv.idade_meses || ' mes(es)'
        else
            floor(cv.idade_meses / 12)::int || ' ano(s) ' || (cv.idade_meses % 12) || ' mes(es)'
    end as "IDADE",
    cv.no_imunobiologico as "IMUNO",
    cv.no_dose_imunobiologico as "DOSE"
from public.calendario_vacinal cv
where cv.co_grupo_alvo = 'CRIANCAS'
  and cv.co_status_vacina = 'ATRASADA'
  and cv.idade_meses < 12   -- apenas até 11 meses e 29 dias
order by 1,2;
