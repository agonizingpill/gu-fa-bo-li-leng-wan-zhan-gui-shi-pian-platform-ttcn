import {request} from '../api.js';
import {display, el} from '../dom.js';
import {evidence} from '../store.js';
import {status} from '../widgets.js';
import {workspace} from '../workspace.js';

const page = {
  "title": "温度 × 片厚 · 拟合曲线",
  "module": "预测曲线签注",
  "caption": "预测曲线签注",
  "detail": "将非线性交互与线性项同时纳入 Lasso，留下末段温区用于误差比较。",
  "path": "/profiles",
  "columns": [
    {
      "name": "code",
      "label": "编号"
    },
    {
      "name": "coupon",
      "label": "基准试片"
    },
    {
      "name": "prediction",
      "label": "拟合弯度 mm"
    },
    {
      "name": "mae",
      "label": "留出 MAE mm"
    },
    {
      "name": "curve",
      "label": "改善说明"
    },
    {
      "name": "token",
      "label": "拟合编号"
    }
  ],
  "layout": "split",
  "view": "grid",
  "actions": [
    {
      "name": "fit_curve",
      "label": "计算试片拟合曲线",
      "path": "/profiles/fit-curve",
      "fields": [
        {
          "name": "coupon",
          "label": "验证试片",
          "kind": "text",
          "initial": "GP-NEW"
        },
        {
          "name": "penalty",
          "label": "Lasso 正则强度",
          "kind": "float",
          "initial": 0.035
        }
      ],
      "help": "拟合保温温度、片厚、目标弯度之间的二次交互。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "sweep_curve",
      "label": "比选正则强度档位",
      "path": "/profiles/sweep-curve",
      "fields": [
        {
          "name": "coupon",
          "label": "基准试片",
          "kind": "text",
          "initial": "GP-NEW"
        },
        {
          "name": "penalties",
          "label": "正则强度档位（JSON 数组）",
          "kind": "json",
          "initial": [0.01, 0.035, 0.1]
        }
      ],
      "help": "各档沿用开跑时封存的试片分组，按训练侧交叉验证误差定档，定档后才测胜档留出误差；中断续跑时不重复记分。",
      "roles": [
        "operator",
        "reviewer"
      ],
      "success": "已写入"
    },
    {
      "name": "sign_profile",
      "label": "签注拟合曲线",
      "path": "/profiles/sign-profile",
      "fields": [
        {
          "name": "code",
          "label": "曲线版本",
          "kind": "text",
          "initial": "PRO-24"
        },
        {
          "name": "token",
          "label": "计算编号",
          "kind": "token",
          "initial": ""
        }
      ],
      "help": "核对留出误差后签注曲线。一个计算编号只允许签注一次。",
      "roles": [
        "reviewer"
      ],
      "success": "已写入"
    }
  ]
};

function auditView(row) {
  const curve = row.curve || {};
  const pairs = [
    ['曲线版本', row.code],
    ['基准试片', row.coupon],
    ['拟合弯度 mm', row.prediction],
    ['胜档留出 MAE mm', row.mae],
    ['拟合编号', row.token]
  ];
  if (curve.penalty !== undefined) pairs.push(['胜档正则强度', curve.penalty]);
  if (Array.isArray(curve.tiers))
    pairs.push(['各档交叉验证 MAE mm', curve.tiers.map(tier => tier.penalty + ' → ' + tier.cv_mae).join('；')]);
  if (curve.grouping) {
    pairs.push(['训练分组', curve.grouping.train.join('、')]);
    pairs.push(['留出分组', curve.grouping.holdout.join('、')]);
  }
  if (Array.isArray(curve.terms)) pairs.push(['保留项', curve.terms]);
  return el('article', {class:'record'}, el('h3', {}, '核对 ' + row.code),
    el('dl', {}, pairs.flatMap(([key, value]) => [el('dt', {}, key), el('dd', {}, display(value))])));
}

function auditPanel() {
  const output = el('div', {class:'audit-output'});
  const form = el('form', {class:'action', id:'audit_lookup'},
    el('h3', {}, '按编号核对曲线'),
    el('p', {}, '计算记录过期后，仍可按拟合编号核对原分组、各档误差和胜档留出误差。'),
    el('div', {class:'fields'}, el('label', {}, el('span', {}, '拟合编号'),
      el('input', {name:'token', required:'', type:'text', value:evidence.get()}))),
    el('button', {type:'submit'}, '核对'));
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const token = String(new FormData(form).get('token')).trim();
    try {
      const row = await request('/profiles/audit/' + encodeURIComponent(token));
      output.replaceChildren(auditView(row));
    } catch (error) {
      output.replaceChildren(status(error.message, 'error'));
    }
  });
  return el('section', {class:'audit'}, form, output);
}

export const {title} = page;
export const key = "profiles";
export async function render(root, role) {
  await workspace(root, role, page);
  root.appendChild(auditPanel());
}
