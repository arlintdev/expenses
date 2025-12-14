import { useParams, useNavigate } from 'react-router-dom';
import ExpenseEdit from '../components/ExpenseEdit';

function ExpenseEditRoute({ apiUrl }) {
  const { id } = useParams();
  const navigate = useNavigate();

  const handleSave = () => {
    navigate(-1); // Go back to previous page
  };

  const handleCancel = () => {
    navigate(-1);
  };

  return (
    <ExpenseEdit
      apiUrl={apiUrl}
      expenseId={id}
      onSave={handleSave}
      onCancel={handleCancel}
    />
  );
}

export default ExpenseEditRoute;
