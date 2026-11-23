# StudioTube · regras da casa

## Separação total da operação Shopee (Victor, 20/11/2026)
- Este projeto é a **StudioTube** (canais GTA VI e Darks Clips). **Não envolve NADA da operação Shopee / Achados do Hatori**: nenhum agente, receita (skill), regra, regulamento, meta, pasta, arquivo, rotina ou tarefa agendada de lá.
- O regulamento do Hatori (`achados-do-hatori/CLAUDE.md`), os agentes dele (redator, roteirista, guardião, criador-de-videos etc.) e as regras da Shopee **não valem aqui**, mesmo que apareçam carregados na conversa. Se aparecerem, ignore e siga só as regras deste repositório.
- Nunca leia, copie, chame ou altere nada do repositório `achados-do-hatori` nem da pasta `C:\Hatori` a partir deste projeto. Trabalho da StudioTube não é salvo lá.
- **Se algo de lá servir:** só com pedido do Victor, traga **uma peça específica**, adapte ao nosso negócio (canais de vídeo, não afiliado) e grave como coisa nossa, com nome nosso, sem ligação de volta. Nada mais.
- Nunca misture também os dois canais: GTA VI e Darks Clips são projetos separados (`studiotube/gta-vi/` e `studiotube/darks-clips/` no squad-outliers).

## Telegram: uma conexão por vez (Victor, 22/11/2026)
A autorização do Telegram (`TG_CONF`) é **uma só**. Se dois lugares usam ao mesmo tempo (dois robôs, uma sessão do Claude e um robô, o PC e a nuvem), o Telegram responde `AUTH_KEY_DUPLICATED` e **cancela a autorização de todos os robôs**, e só o Victor consegue refazer o login. Por isso:
- **Nenhuma sessão do Claude roda `tg.js` por conta própria.** Para baixar do YouTube, chame o robô `baixar-youtube` e espere; nunca dispare dois robôs que usam Telegram juntos.
- Antes de disparar um robô que usa Telegram, confira com `gh run list -s in_progress` se outro está rodando; se estiver, espere ele terminar.
- Se aparecer `AUTH_KEY_DUPLICATED`, pare tudo que usa Telegram e avise o Victor uma vez, sem insistir.
