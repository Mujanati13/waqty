import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, Tabs, message, Typography } from 'antd';
import { UserOutlined, LockOutlined, BankOutlined, IdcardOutlined } from '@ant-design/icons';
import { loginESN, loginConsultant } from '../services/authService';

const { Title, Text } = Typography;

const Login = () => {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('consultant');
  const navigate = useNavigate();

  const handleLogin = async (values) => {
    setLoading(true);
    try {
      let result;
      if (activeTab === 'esn') {
        result = await loginESN(values.email, values.password);
      } else {
        result = await loginConsultant(values.email, values.password);
      }

      if (result.success) {
        message.success('Connexion réussie !');
        if (activeTab === 'esn') {
          navigate('/esn/dashboard');
        } else {
          navigate('/consultant/cra');
        }
      } else {
        message.error(result.error || 'Échec de la connexion');
      }
    } catch (error) {
      message.error('Erreur de connexion');
    } finally {
      setLoading(false);
    }
  };

  const tabItems = [
    {
      key: 'consultant',
      label: (
        <span>
          <IdcardOutlined /> Consultant
        </span>
      ),
    },
    {
      key: 'esn',
      label: (
        <span>
          <BankOutlined /> ESN
        </span>
      ),
    },
  ];

  return (
    <div style={styles.container}>
      <Card style={styles.card}>
        <div style={styles.header}>
          <Title level={2} style={styles.title}>
            MCI Mini
          </Title>
          <Text type="secondary">Gestion des Comptes Rendus d'Activité</Text>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          centered
          style={styles.tabs}
        />

        <Form
          name="login"
          onFinish={handleLogin}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="email"
            rules={[
              { required: true, message: 'Veuillez entrer votre email' },
              { type: 'email', message: 'Email invalide' },
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="Email"
              autoComplete="email"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: 'Veuillez entrer votre mot de passe' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Mot de passe"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={styles.button}
            >
              {loading ? 'Connexion...' : 'Se connecter'}
            </Button>
          </Form.Item>
        </Form>

        <div style={styles.footer}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {activeTab === 'esn' 
              ? 'Connectez-vous en tant qu\'ESN pour gérer vos consultants'
              : 'Connectez-vous en tant que consultant pour saisir vos CRA'
            }
          </Text>
        </div>
      </Card>
    </div>
  );
};

const styles = {
  container: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    padding: 20,
  },
  card: {
    width: '100%',
    maxWidth: 400,
    boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
    borderRadius: 12,
  },
  header: {
    textAlign: 'center',
    marginBottom: 24,
  },
  title: {
    margin: 0,
    color: '#1890ff',
  },
  tabs: {
    marginBottom: 16,
  },
  button: {
    height: 45,
    fontWeight: 600,
  },
  footer: {
    textAlign: 'center',
    marginTop: 16,
  },
};

export default Login;
